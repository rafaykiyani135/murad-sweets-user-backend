"""
Temporary /history router — provides unauthenticated admin visibility into
order history and current inventory levels.

NOTE: This is intentionally unauthenticated for now. When migrated to the
real /admin panel, JWT protection will be added.
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.customer import Customer
from app.models.category import Category
from app.schemas.orders import OrderSummary
from app.schemas.inventory import StockSummary
from app.services.inventory import deduct_inventory, restore_inventory
from app.services.order_numbers import generate_order_number

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class HistoryStatusUpdate(BaseModel):
    status: str  # "pending" | "completed" | "cancelled"


from typing import Optional

class ManualOrderItem(BaseModel):
    product_id: str   # UUID string of the product
    quantity: int
    selections: Optional[dict] = None


class ManualOrderCreate(BaseModel):
    customer_name: str
    customer_email: EmailStr
    customer_phone: str
    fulfillment_type: str = "pickup"   # "pickup" | "delivery"
    scheduled_date: str                # YYYY-MM-DD
    scheduled_slot: str = "Morning (10:00 AM – 1:00 PM)"
    payment_method: str = "cod"
    notes: str = ""
    items: List[ManualOrderItem]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=List[OrderSummary])
async def history_orders(
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Return a lightweight list of all orders (newest first).
    Used by the /history dashboard to display order history.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    orders = result.scalars().all()

    summaries = []
    for order in orders:
        summaries.append(OrderSummary(
            order_number=order.order_number,
            status=order.status,
            customer_name=order.customer.full_name if order.customer else "Unknown",
            total=order.total_cents / 100.0,
            scheduled_date=order.scheduled_date.isoformat(),
            item_count=sum(item.quantity for item in order.items),
            fulfillment_type=order.fulfillment_type,
            created_at=order.created_at,
        ))

    return summaries


@router.patch("/orders/{order_number}/status", response_model=OrderSummary)
async def history_update_order_status(
    order_number: str,
    payload: HistoryStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update the status of an order to: pending, completed, or cancelled.
    When cancelled, inventory is automatically restored.
    """
    allowed = {"pending", "completed", "cancelled"}
    if payload.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of: {', '.join(sorted(allowed))}"
        )

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    previous_status = order.status

    # Restore inventory only when transitioning TO cancelled for the first time
    if payload.status == "cancelled" and previous_status != "cancelled":
        await restore_inventory(db, order)

    order.status = payload.status
    await db.commit()

    return OrderSummary(
        order_number=order.order_number,
        status=order.status,
        customer_name=order.customer.full_name if order.customer else "Unknown",
        total=order.total_cents / 100.0,
        scheduled_date=order.scheduled_date.isoformat(),
        item_count=sum(item.quantity for item in order.items),
        fulfillment_type=order.fulfillment_type,
        created_at=order.created_at,
    )


@router.post("/orders", response_model=OrderSummary, status_code=201)
async def history_create_manual_order(
    payload: ManualOrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually create an order from the dashboard.
    Deducts inventory for each ordered item and generates a proper order number.
    """
    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one item is required.")

    # Parse + validate scheduled date
    try:
        scheduled_date = datetime.strptime(payload.scheduled_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # ── Resolve products & build validated items ──────────────────────────────
    validated_items = []
    subtotal_cents = 0

    for entry in payload.items:
        try:
            import uuid
            product_uuid = uuid.UUID(entry.product_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid product ID: {entry.product_id}")

        prod_result = await db.execute(select(Product).where(Product.id == product_uuid))
        product = prod_result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product not found: {entry.product_id}")
        if not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product '{product.name}' is inactive.")

        if entry.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be at least 1.")

        line_total = product.base_price_cents * entry.quantity
        subtotal_cents += line_total

        validated_items.append({
            "product_id": product.id,
            "name_snapshot": product.name,
            "unit_price_cents": product.base_price_cents,
            "quantity": entry.quantity,
            "line_total_cents": line_total,
            "selections": entry.selections,
        })

    # ── Find or create customer ───────────────────────────────────────────────
    cust_result = await db.execute(
        select(Customer).where(Customer.email == payload.customer_email)
    )
    customer = cust_result.scalar_one_or_none()
    if not customer:
        customer = Customer(
            full_name=payload.customer_name,
            email=payload.customer_email,
            phone=payload.customer_phone,
        )
        db.add(customer)
        await db.flush()
    else:
        customer.full_name = payload.customer_name
        customer.phone = payload.customer_phone

    # ── Create order ──────────────────────────────────────────────────────────
    order_number = await generate_order_number(db)
    order = Order(
        order_number=order_number,
        customer_id=customer.id,
        status="pending",
        fulfillment_type=payload.fulfillment_type,
        scheduled_date=scheduled_date,
        scheduled_slot=payload.scheduled_slot,
        subtotal_cents=subtotal_cents,
        delivery_fee_cents=0,
        tax_cents=0,
        total_cents=subtotal_cents,
        payment_method=payload.payment_method,
        payment_status="pending",
        notes=payload.notes or None,
        admin_notes="Manually created via dashboard",
    )
    db.add(order)
    await db.flush()

    # ── Save order items ──────────────────────────────────────────────────────
    for item in validated_items:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item["product_id"],
            name_snapshot=item["name_snapshot"],
            unit_price_cents=item["unit_price_cents"],
            quantity=item["quantity"],
            line_total_cents=item["line_total_cents"],
            selections=item["selections"],
        ))

    # ── Deduct inventory (same transaction) ───────────────────────────────────
    await deduct_inventory(db, validated_items)

    await db.commit()

    # Reload for response
    reload_result = await db.execute(
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .where(Order.id == order.id)
    )
    order = reload_result.scalar_one()

    return OrderSummary(
        order_number=order.order_number,
        status=order.status,
        customer_name=order.customer.full_name,
        total=order.total_cents / 100.0,
        scheduled_date=order.scheduled_date.isoformat(),
        item_count=sum(item.quantity for item in order.items),
        fulfillment_type=order.fulfillment_type,
        created_at=order.created_at,
    )


@router.get("/stock", response_model=List[StockSummary])
async def history_stock(db: AsyncSession = Depends(get_db)):
    """
    Return all products that have quantity tracking enabled (quantity_on_hand IS NOT NULL).
    Pitha, party trays, and custom_box containers are excluded (they have NULL).
    """
    result = await db.execute(
        select(Product)
        .join(Category)
        .options(selectinload(Product.category))
        .where(Product.quantity_on_hand.is_not(None))
        .where(Product.is_active == True)
        .order_by(Category.sort_order, Product.name)
    )
    products = result.scalars().all()

    return [
        StockSummary(
            product_id=p.id,
            slug=p.slug,
            name=p.name,
            category=p.category.name if p.category else "Unknown",
            product_type=p.product_type,
            quantity_on_hand=p.quantity_on_hand,
            is_in_stock=p.is_in_stock,
        )
        for p in products
    ]
