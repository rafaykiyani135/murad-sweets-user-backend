"""
Admin CRUD endpoints for managing Categories and Products.
These endpoints power the /history dashboard "Products" tab.
All changes reflect immediately on the public menu.
"""

import uuid
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.category import Category
from app.models.product import Product
from app.models.admin_user import AdminUser
from app.api.v1.auth import get_current_admin_from_cookie

router = APIRouter()


# ─── Helper ──────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class ProductCreate(BaseModel):
    category_id: str
    name: str
    description: Optional[str] = None
    base_price_cents: int = 0
    unit_label: Optional[str] = None
    product_type: str = "standard"
    min_quantity: int = 1
    max_quantity: Optional[int] = None
    is_active: bool = True
    is_in_stock: bool = True
    quantity_on_hand: Optional[int] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price_cents: Optional[int] = None
    unit_label: Optional[str] = None
    is_active: Optional[bool] = None
    is_in_stock: Optional[bool] = None
    quantity_on_hand: Optional[int] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    category_id: Optional[str] = None


# ─── Category Endpoints ───────────────────────────────────────────────────────

@router.get("/categories")
async def admin_list_categories(db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin_from_cookie)):
    """List ALL categories including inactive ones, with their products."""
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.products))
        .order_by(Category.sort_order, Category.name)
    )
    cats = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "slug": c.slug,
            "name": c.name,
            "description": c.description,
            "sort_order": c.sort_order,
            "is_active": c.is_active,
            "product_count": len(c.products),
            "products": [
                {
                    "id": str(p.id),
                    "slug": p.slug,
                    "name": p.name,
                    "description": p.description,
                    "base_price_cents": p.base_price_cents,
                    "unit_label": p.unit_label,
                    "product_type": p.product_type,
                    "min_quantity": p.min_quantity,
                    "max_quantity": p.max_quantity,
                    "is_active": p.is_active,
                    "is_in_stock": p.is_in_stock,
                    "quantity_on_hand": p.quantity_on_hand,
                    "category_id": str(p.category_id),
                }
                for p in sorted(c.products, key=lambda x: x.name)
            ]
        }
        for c in cats
    ]


@router.post("/categories", status_code=201)
async def admin_create_category(payload: CategoryCreate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin_from_cookie)):
    """Create a new category."""
    slug = slugify(payload.name)
    # Ensure slug is unique
    existing = await db.execute(select(Category).where(Category.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    cat = Category(
        slug=slug,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {"id": str(cat.id), "slug": cat.slug, "name": cat.name, "is_active": cat.is_active}


@router.patch("/categories/{category_id}")
async def admin_update_category(category_id: str, payload: CategoryUpdate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin_from_cookie)):
    """Update a category's name, description, sort order, or active status."""
    result = await db.execute(select(Category).where(Category.id == uuid.UUID(category_id)))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    if payload.name is not None:
        cat.name = payload.name
    if payload.description is not None:
        cat.description = payload.description
    if payload.sort_order is not None:
        cat.sort_order = payload.sort_order
    if payload.is_active is not None:
        cat.is_active = payload.is_active

    await db.commit()
    return {"id": str(cat.id), "slug": cat.slug, "name": cat.name, "is_active": cat.is_active}


@router.delete("/categories/{category_id}")
async def admin_delete_category(category_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin_from_cookie)):
    """Delete a category and all its products (cascade)."""
    result = await db.execute(select(Category).where(Category.id == uuid.UUID(category_id)))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(cat)
    await db.commit()
    return {"deleted": True}


# ─── Product Endpoints ────────────────────────────────────────────────────────

@router.post("/products", status_code=201)
async def admin_create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin_from_cookie)):
    """Create a new product inside a category."""
    try:
        cat_uuid = uuid.UUID(payload.category_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category_id")

    cat_result = await db.execute(select(Category).where(Category.id == cat_uuid))
    if not cat_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Category not found")

    slug = slugify(payload.name)
    existing = await db.execute(select(Product).where(Product.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    product = Product(
        category_id=cat_uuid,
        slug=slug,
        name=payload.name,
        description=payload.description,
        base_price_cents=payload.base_price_cents,
        unit_label=payload.unit_label,
        product_type=payload.product_type,
        min_quantity=payload.min_quantity,
        max_quantity=payload.max_quantity,
        is_active=payload.is_active,
        is_in_stock=payload.is_in_stock,
        quantity_on_hand=payload.quantity_on_hand,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return {
        "id": str(product.id),
        "slug": product.slug,
        "name": product.name,
        "base_price_cents": product.base_price_cents,
        "is_active": product.is_active,
    }


@router.patch("/products/{product_id}")
async def admin_update_product(product_id: str, payload: ProductUpdate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin_from_cookie)):
    """Update any field on a product."""
    result = await db.execute(select(Product).where(Product.id == uuid.UUID(product_id)))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if payload.name is not None:
        product.name = payload.name
    if payload.description is not None:
        product.description = payload.description
    if payload.base_price_cents is not None:
        product.base_price_cents = payload.base_price_cents
    if payload.unit_label is not None:
        product.unit_label = payload.unit_label
    if payload.is_active is not None:
        product.is_active = payload.is_active
    if payload.is_in_stock is not None:
        product.is_in_stock = payload.is_in_stock
    if payload.quantity_on_hand is not None:
        product.quantity_on_hand = payload.quantity_on_hand
    if payload.min_quantity is not None:
        product.min_quantity = payload.min_quantity
    if payload.max_quantity is not None:
        product.max_quantity = payload.max_quantity
    if payload.category_id is not None:
        product.category_id = uuid.UUID(payload.category_id)

    await db.commit()
    await db.refresh(product)
    return {
        "id": str(product.id),
        "name": product.name,
        "base_price_cents": product.base_price_cents,
        "is_active": product.is_active,
    }


@router.delete("/products/{product_id}")
async def admin_delete_product(product_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin_from_cookie)):
    """Delete a product permanently."""
    result = await db.execute(select(Product).where(Product.id == uuid.UUID(product_id)))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.delete(product)
    await db.commit()
    return {"deleted": True}
