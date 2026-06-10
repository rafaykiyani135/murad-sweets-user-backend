"""
Temporary /history router — provides unauthenticated admin visibility into
order history and current inventory levels.

NOTE: This is intentionally unauthenticated for now. When migrated to the
real /admin panel, JWT protection will be added.
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.order import Order
from app.models.product import Product
from app.models.category import Category
from app.schemas.orders import OrderSummary
from app.schemas.inventory import StockSummary

router = APIRouter()


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
