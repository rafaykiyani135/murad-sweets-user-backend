from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr

class AdminLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ProductAvailabilityUpdate(BaseModel):
    is_in_stock: bool

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price_cents: Optional[int] = None
    unit_label: Optional[str] = None
    is_active: Optional[bool] = None
    is_in_stock: Optional[bool] = None
    preorder_only: Optional[bool] = None
    prep_time_hours: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class ProductCreate(BaseModel):
    category_id: str
    slug: str
    name: str
    description: Optional[str] = None
    base_price_cents: int
    unit_label: Optional[str] = None
    product_type: str = "standard"
    min_quantity: int = 1
    max_quantity: Optional[int] = None
    is_active: bool = True
    is_in_stock: bool = True
    preorder_only: bool = False
    prep_time_hours: int = 0
    metadata: Optional[Dict[str, Any]] = None

class CategoryCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class SettingsUpdate(BaseModel):
    pickup_address: Optional[str] = None
    pickup_instructions: Optional[str] = None
    delivery_zones: Optional[List[str]] = None
    delivery_fee_cents: Optional[int] = None
    delivery_minimum_cents: Optional[int] = None
    time_slots: Optional[List[str]] = None
    payment_methods: Optional[List[str]] = None
