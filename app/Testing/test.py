import asyncio
from app.db.session import SessionLocal
from sqlalchemy import select
from app.models.product import Product

async def main():
    async with SessionLocal() as db:
        res = await db.execute(select(Product))
        products = res.scalars().all()
        for p in products:
            print(p.id, p.name, p.slug)

asyncio.run(main())