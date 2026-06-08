from sqlalchemy import select, func
from app.models.order import Order

async def generate_order_number(db) -> str:
    """
    Generate a unique, sequential order number (e.g., MS-100001).
    """
    result = await db.execute(select(func.count(Order.id)))
    count = result.scalar() or 0
    return f"MS-{100001 + count}"
