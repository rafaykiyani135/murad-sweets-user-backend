from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.category import Category
from app.models.product import Product
from app.schemas.catalog import CategoryOut, ProductOut, StoreSettingsOut
from app.services.pricing import ALLOWED_ZIP_CODES, DELIVERY_FEE_CENTS, DELIVERY_MINIMUM_CENTS

router = APIRouter()

@router.get("/categories", response_model=List[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """List all active product categories."""
    result = await db.execute(
        select(Category)
        .where(Category.is_active == True)
        .order_by(Category.sort_order)
    )
    return result.scalars().all()

@router.get("/products", response_model=List[ProductOut])
async def list_products(
    category: Optional[str] = None,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List active products. Optionally filter by category slug or search query.
    """
    query = (
        select(Product)
        .options(selectinload(Product.options))
        .where(Product.is_active == True)
    )
    
    if category:
        query = query.join(Category).where(Category.slug == category)
        
    if q:
        query = query.where(
            or_(
                Product.name.ilike(f"%{q}%"),
                Product.description.ilike(f"%{q}%")
            )
        )
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/products/{slug}", response_model=ProductOut)
async def get_product(slug: str, db: AsyncSession = Depends(get_db)):
    """Retrieve product detail by URL slug."""
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.options))
        .where(Product.slug == slug, Product.is_active == True)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/collections/{cat_slug}", response_model=List[ProductOut])
async def get_collection(cat_slug: str, db: AsyncSession = Depends(get_db)):
    """List products for a specific category slug."""
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.options))
        .join(Category)
        .where(Category.slug == cat_slug, Product.is_active == True)
    )
    return result.scalars().all()

@router.get("/store/settings", response_model=StoreSettingsOut)
async def get_store_settings():
    """Retrieve store settings: Pickup instructions, time slots, payment methods, delivery zones."""
    return StoreSettingsOut(
        pickup_address="Brooklyn, NY 11218",
        pickup_instructions="Pickup is contact-free. The exact pickup location details will be sent in your confirmation email/SMS.",
        delivery_zones=list(ALLOWED_ZIP_CODES),
        delivery_fee_cents=DELIVERY_FEE_CENTS,
        delivery_minimum_cents=DELIVERY_MINIMUM_CENTS,
        time_slots=[
            "Morning (10:00 AM – 1:00 PM)",
            "Afternoon (1:00 PM – 5:00 PM)",
            "Evening (5:00 PM – 8:00 PM)"
        ],
        payment_methods=["cod", "card"]
    )
