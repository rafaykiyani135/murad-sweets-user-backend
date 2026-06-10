import uuid
from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.admin_user import AdminUser
from app.models.order import Order
from app.models.inquiry import Inquiry
from app.models.product import Product
from app.models.category import Category
from app.schemas.admin import AdminLogin, Token, ProductAvailabilityUpdate, ProductUpdate, ProductCreate, RestockUpdate
from app.schemas.orders import OrderOut, OrderStatusUpdate, OrderNotesUpdate
from app.schemas.inquiries import InquiryOut, InquiryStatusUpdate
from app.schemas.catalog import ProductOut
from app.core import security
from app.core.config import settings
from app.api.v1.orders import serialize_order
from app.services.inventory import restore_inventory

router = APIRouter()
security_bearer = HTTPBearer()

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> AdminUser:
    """Dependency to authorize administrative endpoints using JWT tokens."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    admin = result.scalar_one_or_none()
    if admin is None or not admin.is_active:
        raise credentials_exception
    return admin

@router.post("/auth/login", response_model=Token)
async def login(payload: AdminLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate admin credentials and return a JWT access token."""
    result = await db.execute(select(AdminUser).where(AdminUser.username == payload.username))
    admin = result.scalar_one_or_none()
    
    if not admin or not security.verify_password(payload.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
        
    access_token = security.create_access_token(subject=admin.username)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/orders", response_model=List[OrderOut])
async def list_admin_orders(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Retrieve a paginated list of all customer orders (newest first)."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    orders = result.scalars().all()
    return [serialize_order(o) for o in orders]

@router.get("/orders/{order_number}", response_model=OrderOut)
async def get_admin_order(
    order_number: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Retrieve full details of an order, including individual items, by order number."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_order(order)

@router.patch("/orders/{order_number}/status", response_model=OrderOut)
async def update_order_status(
    order_number: str,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Advance an order through its lifecycle (pending -> confirmed -> preparing etc.)."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    previous_status = order.status
    order.status = payload.status

    # Restore inventory if order is being cancelled for the first time
    if payload.status == "cancelled" and previous_status != "cancelled":
        await restore_inventory(db, order)

    await db.commit()
    return serialize_order(order)

@router.patch("/orders/{order_number}/notes", response_model=OrderOut)
async def update_order_notes(
    order_number: str,
    payload: OrderNotesUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Append internal administrative notes to a customer order."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.customer), selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order.admin_notes = payload.admin_notes
    await db.commit()
    return serialize_order(order)

@router.get("/contact-inquiries", response_model=List[InquiryOut])
async def list_admin_inquiries(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Retrieve all submitted customer contact inquiries."""
    result = await db.execute(select(Inquiry).order_by(Inquiry.created_at.desc()))
    return result.scalars().all()

@router.patch("/contact-inquiries/{id}", response_model=InquiryOut)
async def update_inquiry_status(
    id: uuid.UUID,
    payload: InquiryStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Update contact inquiry status (e.g., pending -> read -> resolved)."""
    result = await db.execute(select(Inquiry).where(Inquiry.id == id))
    inquiry = result.scalar_one_or_none()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
        
    inquiry.status = payload.status
    await db.commit()
    await db.refresh(inquiry)
    return inquiry

@router.patch("/products/{id}/availability", response_model=ProductOut)
async def toggle_product_availability(
    id: uuid.UUID,
    payload: ProductAvailabilityUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Toggle a product's in-stock status (inStock: true / false)."""
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.options))
        .where(Product.id == id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    product.is_in_stock = payload.is_in_stock
    await db.commit()
    return product

@router.post("/products", response_model=ProductOut)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Add a new product to the catalog."""
    cat_uuid = uuid.UUID(payload.category_id)
    cat_result = await db.execute(select(Category).where(Category.id == cat_uuid))
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    product = Product(
        category_id=cat_uuid,
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        base_price_cents=payload.base_price_cents,
        unit_label=payload.unit_label,
        product_type=payload.product_type,
        min_quantity=payload.min_quantity,
        max_quantity=payload.max_quantity,
        is_active=payload.is_active,
        is_in_stock=payload.is_in_stock,
        preorder_only=payload.preorder_only,
        prep_time_hours=payload.prep_time_hours,
        metadata_json=payload.metadata
    )
    db.add(product)
    await db.commit()
    
    # Reload product with options
    res = await db.execute(
        select(Product)
        .options(selectinload(Product.options))
        .where(Product.id == product.id)
    )
    return res.scalar_one()

@router.patch("/products/{id}", response_model=ProductOut)
async def update_product(
    id: uuid.UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Edit an existing product's fields."""
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.options))
        .where(Product.id == id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    for field, val in payload.model_dump(exclude_unset=True).items():
        if field == "metadata":
            product.metadata_json = val
        else:
            setattr(product, field, val)
            
    await db.commit()
    return product


@router.patch("/products/{id}/restock", response_model=ProductOut)
async def restock_product(
    id: uuid.UUID,
    payload: RestockUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Add stock quantity to a product. Initializes tracking if previously untracked (NULL)."""
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.options))
        .where(Product.id == id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Restock quantity must be greater than 0.")

    # Initialize tracking if this product was previously untracked (NULL)
    if product.quantity_on_hand is None:
        product.quantity_on_hand = payload.quantity
    else:
        product.quantity_on_hand += payload.quantity

    # Auto-set in_stock when quantity goes above 0
    if product.quantity_on_hand > 0:
        product.is_in_stock = True

    await db.commit()
    await db.refresh(product)
    return product
