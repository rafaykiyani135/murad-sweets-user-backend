from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.schemas.orders import OrderCreate, OrderOut, OrderContactInfo, OrderItemOut
from app.services.pricing import calculate_quote
from app.services.scheduling import validate_schedule
from app.services.order_numbers import generate_order_number
from app.services.payments import create_checkout_session, check_payment_intent_status
from app.services.notifications import send_order_confirmation_emails
from app.services.inventory import deduct_inventory

router = APIRouter()

def serialize_order(order: Order, client_secret: str = None, checkout_url: str = None) -> OrderOut:
    """Helper to convert database Order models to OrderOut schemas."""
    contact = OrderContactInfo(
        fullName=order.customer.full_name,
        email=order.customer.email,
        phone=order.customer.phone,
        notes=order.notes
    )
    
    items_out = []
    for item in order.items:
        items_out.append(OrderItemOut(
            id=item.id,
            product_id=item.product_id,
            option_id=item.option_id,
            name_snapshot=item.name_snapshot,
            unit_price_cents=item.unit_price_cents,
            unit_price=item.unit_price_cents / 100.0,
            quantity=item.quantity,
            line_total_cents=item.line_total_cents,
            line_total=item.line_total_cents / 100.0,
            selections=item.selections
        ))
        
    return OrderOut(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        fulfillment_type=order.fulfillment_type,
        scheduled_date=order.scheduled_date.isoformat(),
        scheduled_slot=order.scheduled_slot,
        street=order.street,
        city=order.city,
        state=order.state,
        zip_code=order.zip_code,
        subtotal_cents=order.subtotal_cents,
        delivery_fee_cents=order.delivery_fee_cents,
        tax_cents=order.tax_cents,
        total_cents=order.total_cents,
        subtotal=order.subtotal_cents / 100.0,
        delivery_fee=order.delivery_fee_cents / 100.0,
        tax=order.tax_cents / 100.0,
        total=order.total_cents / 100.0,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        client_secret=client_secret,
        checkout_url=checkout_url,
        admin_notes=order.admin_notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        contact=contact,
        items=items_out
    )

@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Create a new order:
    1. Recalculates cart quote based on DB prices.
    2. Validates preorder lead times and slots.
    3. Links or creates a guest customer profile by email.
    4. Creates the Order and snapshotted OrderItems.
    5. Optionally initiates Stripe PaymentIntent for card options.
    6. Triggers background notification emails.
    """
    # 1. Recalculate quote
    items_list = [item.model_dump() for item in payload.items]
    quote = await calculate_quote(
        db=db,
        items=items_list,
        fulfillment_type=payload.fulfillment,
        zip_code=payload.zip
    )
    
    # 1.5 Apply delivery fee from frontend
    if payload.fulfillment == "delivery":
        quote["delivery_fee_cents"] = payload.deliveryFeeCents or 0
        quote["total_cents"] = quote["subtotal_cents"] + quote["tax_cents"] + quote["delivery_fee_cents"]
    
    # 2. Validate schedule
    try:
        scheduled_date = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
    validate_schedule(scheduled_date, payload.slot, quote["max_prep_time_hours"])
    
    # 3. Find or create customer
    customer_res = await db.execute(
        select(Customer).where(Customer.email == payload.email)
    )
    customer = customer_res.scalar_one_or_none()
    
    if not customer:
        customer = Customer(
            full_name=payload.fullName,
            email=payload.email,
            phone=payload.phone
        )
        db.add(customer)
        await db.flush()  # Obtain customer ID
    else:
        # Update name/phone to match latest checkout details
        customer.full_name = payload.fullName
        customer.phone = payload.phone
        
    # 4. Generate sequential order number
    order_number = await generate_order_number(db)
    
    # 5. Save order (always — before any payment redirect)
    order = Order(
        order_number=order_number,
        customer_id=customer.id,
        status="pending",
        fulfillment_type=payload.fulfillment,
        scheduled_date=scheduled_date,
        scheduled_slot=payload.slot,
        street=payload.street,
        city=payload.city,
        state=payload.state,
        zip_code=payload.zip,
        subtotal_cents=quote["subtotal_cents"],
        delivery_fee_cents=quote["delivery_fee_cents"],
        tax_cents=quote["tax_cents"],
        total_cents=quote["total_cents"],
        payment_method=payload.paymentMethod,
        payment_status="pending",
        notes=payload.notes
    )
    
    db.add(order)
    await db.flush()  # Obtain order ID
    
    # 6. Save items snapshot
    for item in quote["validated_items"]:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item["product_id"],
            option_id=item.get("option_id"),
            name_snapshot=item["name_snapshot"],
            unit_price_cents=item["unit_price_cents"],
            quantity=item["quantity"],
            line_total_cents=item["line_total_cents"],
            selections=item["selections"]
        )
        db.add(order_item)
    
    # 7. Deduct inventory — runs inside the same transaction as the order
    await deduct_inventory(db, quote["validated_items"])
        
    await db.commit()
    
    # Reload order with relations for serialization
    order_detail_res = await db.execute(
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .where(Order.id == order.id)
    )
    order_detail = order_detail_res.scalar_one()
    
    # 8. Now that order is committed, create Stripe Checkout Session for card payments
    checkout_url = None
    if payload.paymentMethod == "card":
        # Extract requesting origin to redirect user back to the correct environment
        origin = request.headers.get("origin") or request.headers.get("referer")
        frontend_url = None
        if origin:
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            if parsed.scheme and parsed.netloc:
                frontend_url = f"{parsed.scheme}://{parsed.netloc}"
        
        try:
            session = create_checkout_session(quote["total_cents"], "usd", order_number, payload.email, frontend_url=frontend_url)
            checkout_url = session.get("checkout_url")
        except Exception as e:
            # Order is already saved — return it with an error so frontend can display a message
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Order #{order_number} was saved but card payment setup failed: {str(e)}. Please contact support."
            )

    # 9. Send notification emails
    send_order_confirmation_emails(
        customer_email=payload.email,
        customer_name=payload.fullName,
        order_number=order_number,
        total_cents=quote["total_cents"],
        fulfillment_type=payload.fulfillment,
        scheduled_date=payload.date,
        scheduled_slot=payload.slot,
        customer_phone=payload.phone,
        delivery_address=f"{payload.street}, {payload.city}, {payload.state} {payload.zip}" if payload.street else None,
        items=[
            {
                "name": item.name_snapshot,
                "quantity": item.quantity,
                "line_total": item.line_total_cents / 100.0,
            }
            for item in order_detail.items
        ],
    )
    
    return serialize_order(order_detail, checkout_url=checkout_url)

@router.get("/{order_number}", response_model=OrderOut)
async def get_order(order_number: str, db: AsyncSession = Depends(get_db)):
    """Look up order details by order number."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Auto-sync Stripe payment status if pending
    if order.payment_method == "card" and order.payment_status == "pending":
        stripe_status = check_payment_intent_status(order.order_number)
        if stripe_status == "succeeded":
            order.payment_status = "paid"
            await db.commit()
        elif stripe_status in ["canceled", "payment_failed"]:
            order.payment_status = "failed"
            await db.commit()

    return serialize_order(order)
