"""
Inventory service — handles stock deduction and restoration.

Rules:
- Products with quantity_on_hand = NULL are never tracked (Pitha, party trays, custom_box containers).
- Deduction is called after OrderItems are saved but before db.commit() so everything is atomic.
- Restoration is called when an order is cancelled, adding stock back.
- When quantity_on_hand reaches 0, is_in_stock is automatically set to False.
- When quantity_on_hand goes above 0, is_in_stock is automatically set to True.
"""

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.product import Product
from app.models.order import Order, OrderItem
from app.services.pricing import get_deterministic_uuid


async def deduct_inventory(
    db: AsyncSession,
    validated_items: List[Dict[str, Any]]
) -> None:
    """
    Deduct stock for each item in the just-created order.
    Called after OrderItems are inserted but before db.commit().

    validated_items is the list produced by calculate_quote(), each entry has:
      - product_id: UUID
      - quantity: int
      - selections: dict | None  (for custom_box items, contains selectedItems)
    """
    for item in validated_items:
        product_id = item["product_id"]
        quantity = item["quantity"]
        selections = item.get("selections")

        # Load the product
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            continue

        if product.product_type == "custom_box":
            # The box container itself is not tracked — deduct each selected sweet
            if selections and "selectedItems" in selections:
                await _deduct_selections(db, selections["selectedItems"])
        else:
            # Standard product — deduct directly
            if product.quantity_on_hand is not None:
                product.quantity_on_hand = max(0, product.quantity_on_hand - quantity)
                if product.quantity_on_hand == 0:
                    product.is_in_stock = False


async def restore_inventory(
    db: AsyncSession,
    order: Order
) -> None:
    """
    Restore stock for all items in a cancelled order.
    Called before db.commit() when order status changes to 'cancelled'.

    Reads order.items (must be pre-loaded via selectinload).
    """
    for item in order.items:
        product_id = item.product_id
        quantity = item.quantity
        selections = item.selections

        if not product_id:
            continue

        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            continue

        if product.product_type == "custom_box":
            # Restore each individually selected sweet
            if selections and "selectedItems" in selections:
                await _restore_selections(db, selections["selectedItems"])
        else:
            if product.quantity_on_hand is not None:
                product.quantity_on_hand += quantity
                if product.quantity_on_hand > 0:
                    product.is_in_stock = True


async def _deduct_selections(
    db: AsyncSession,
    selected_items: List[Dict[str, Any]]
) -> None:
    """Deduct inventory for individual sweets inside a Mix & Match box."""
    for selected in selected_items:
        sweet_id = str(selected.get("id", ""))
        sweet_qty = int(selected.get("quantity", 0))
        if sweet_qty <= 0 or not sweet_id:
            continue

        sweet_db_id = get_deterministic_uuid(sweet_id)
        result = await db.execute(select(Product).where(Product.id == sweet_db_id))
        sweet = result.scalar_one_or_none()
        if not sweet or sweet.quantity_on_hand is None:
            continue

        sweet.quantity_on_hand = max(0, sweet.quantity_on_hand - sweet_qty)
        if sweet.quantity_on_hand == 0:
            sweet.is_in_stock = False


async def _restore_selections(
    db: AsyncSession,
    selected_items: List[Dict[str, Any]]
) -> None:
    """Restore inventory for individual sweets inside a cancelled Mix & Match order."""
    for selected in selected_items:
        sweet_id = str(selected.get("id", ""))
        sweet_qty = int(selected.get("quantity", 0))
        if sweet_qty <= 0 or not sweet_id:
            continue

        sweet_db_id = get_deterministic_uuid(sweet_id)
        result = await db.execute(select(Product).where(Product.id == sweet_db_id))
        sweet = result.scalar_one_or_none()
        if not sweet or sweet.quantity_on_hand is None:
            continue

        sweet.quantity_on_hand += sweet_qty
        if sweet.quantity_on_hand > 0:
            sweet.is_in_stock = True
