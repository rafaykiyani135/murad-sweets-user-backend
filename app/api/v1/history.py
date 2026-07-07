"""
/history router — provides authenticated admin visibility into
order history and current inventory levels.

All endpoints require a valid admin session cookie.
"""

import uuid
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
from app.api.v1.auth import get_current_admin_from_cookie
from app.models.admin_user import AdminUser

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class HistoryStatusUpdate(BaseModel):
    status: str  # "pending" | "completed" | "cancelled"

class HistoryPaymentStatusUpdate(BaseModel):
    payment_status: str  # "pending" | "paid" | "failed" | "refunded"


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
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_from_cookie),
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
            payment_status=order.payment_status,
            payment_method=order.payment_method,
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
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_from_cookie),
):
    """
    Update the status of an order.
    When cancelled, inventory is automatically restored.
    """
    allowed = {"pending", "confirmed", "preparing", "ready", "out_for_delivery", "completed", "cancelled"}
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
        payment_status=order.payment_status,
        payment_method=order.payment_method,
        customer_name=order.customer.full_name if order.customer else "Unknown",
        total=order.total_cents / 100.0,
        scheduled_date=order.scheduled_date.isoformat(),
        item_count=sum(item.quantity for item in order.items),
        fulfillment_type=order.fulfillment_type,
        created_at=order.created_at,
    )


@router.patch("/orders/{order_number}/payment-status", response_model=OrderSummary)
async def history_update_payment_status(
    order_number: str,
    payload: HistoryPaymentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_from_cookie),
):
    """
    Update the payment status of an order.
    """
    allowed = {"pending", "paid", "failed", "refunded"}
    if payload.payment_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Payment status must be one of: {', '.join(sorted(allowed))}"
        )

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.payment_status = payload.payment_status
    await db.commit()

    return OrderSummary(
        order_number=order.order_number,
        status=order.status,
        payment_status=order.payment_status,
        payment_method=order.payment_method,
        customer_name=order.customer.full_name if order.customer else "Unknown",
        total=order.total_cents / 100.0,
        scheduled_date=order.scheduled_date.isoformat(),
        item_count=sum(item.quantity for item in order.items),
        fulfillment_type=order.fulfillment_type,
        created_at=order.created_at,
    )


@router.get("/orders/{order_number}")
async def history_get_order(
    order_number: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_from_cookie),
):
    """
    Get detailed order information by order number.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_number": order.order_number,
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "customer": {
            "full_name": order.customer.full_name if order.customer else "Unknown",
            "email": order.customer.email if order.customer else "",
            "phone": order.customer.phone if order.customer else "",
        },
        "total": order.total_cents / 100.0,
        "scheduled_date": order.scheduled_date.isoformat(),
        "scheduled_slot": order.scheduled_slot,
        "fulfillment_type": order.fulfillment_type,
        "delivery_address": f"{order.street}, {order.city}, {order.state} {order.zip_code}" if order.fulfillment_type == "delivery" and order.street else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "notes": order.notes,
        "admin_notes": order.admin_notes,
        "items": [
            {
                "id": str(item.id),
                "name": item.name_snapshot,
                "unit_price": item.unit_price_cents / 100.0,
                "quantity": item.quantity,
                "line_total": item.line_total_cents / 100.0,
                "selections": item.selections,
            }
            for item in order.items
        ]
    }


@router.post("/orders", response_model=OrderSummary, status_code=201)
async def history_create_manual_order(
    payload: ManualOrderCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_from_cookie),
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
        payment_status=order.payment_status,
        payment_method=order.payment_method,
        customer_name=order.customer.full_name,
        total=order.total_cents / 100.0,
        scheduled_date=order.scheduled_date.isoformat(),
        item_count=sum(item.quantity for item in order.items),
        fulfillment_type=order.fulfillment_type,
        created_at=order.created_at,
    )


@router.get("/stock", response_model=List[StockSummary])
async def history_stock(db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin_from_cookie)):
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


class HistoryStockUpdate(BaseModel):
    quantity_on_hand: int
    is_in_stock: bool


@router.patch("/stock/{product_id}")
async def history_update_stock(
    product_id: uuid.UUID,
    payload: HistoryStockUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_from_cookie),
):
    """
    Update a product's stock levels.
    """
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.quantity_on_hand = payload.quantity_on_hand
    product.is_in_stock = payload.is_in_stock

    await db.commit()
    return {
        "product_id": str(product.id),
        "quantity_on_hand": product.quantity_on_hand,
        "is_in_stock": product.is_in_stock
    }

class HistoryItemSelectionsUpdate(BaseModel):
    selections: dict

@router.patch("/orders/{order_number}/items/{item_id}/selections")
async def history_update_item_selections(
    order_number: str,
    item_id: uuid.UUID,
    payload: HistoryItemSelectionsUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_from_cookie),
):
    """
    Update the Mix & Match selections for a specific order item.
    Adjusts inventory by restoring old selections and deducting new ones.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    target_item = None
    for item in order.items:
        if item.id == item_id:
            target_item = item
            break
            
    if not target_item:
        raise HTTPException(status_code=404, detail="Order item not found")

    # If the order is NOT cancelled, we need to adjust inventory
    if order.status != "cancelled":
        # 1. Restore old selections
        if target_item.selections and "selectedItems" in target_item.selections:
            for old_sel in target_item.selections["selectedItems"]:
                prod_res = await db.execute(select(Product).where(Product.name == old_sel["name"]))
                prod = prod_res.scalars().first()
                if prod and prod.quantity_on_hand is not None:
                    # Restore old_sel["quantity"] * target_item.quantity
                    prod.quantity_on_hand += old_sel["quantity"] * target_item.quantity

        # 2. Deduct new selections
        if payload.selections and "selectedItems" in payload.selections:
            for new_sel in payload.selections["selectedItems"]:
                prod_res = await db.execute(select(Product).where(Product.name == new_sel["name"]))
                prod = prod_res.scalars().first()
                if prod and prod.quantity_on_hand is not None:
                    # Deduct new_sel["quantity"] * target_item.quantity
                    prod.quantity_on_hand -= new_sel["quantity"] * target_item.quantity

    # 3. Update selections
    target_item.selections = payload.selections
    
    await db.commit()
    return {"status": "success"}
