import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class CategoryBase(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

class CategoryOut(CategoryBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CustomBoxRuleOut(BaseModel):
    id: uuid.UUID
    allowed_category_id: uuid.UUID
    exact_selection_count: int
    allow_duplicates: bool
    model_config = ConfigDict(from_attributes=True)

class ProductOptionOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    price_cents: int
    selection_count: int
    is_active: bool
    metadata: Optional[Dict[str, Any]] = None
    custom_box_rules: List[CustomBoxRuleOut] = []
    model_config = ConfigDict(from_attributes=True)

class ProductOut(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    slug: str
    name: str
    description: Optional[str] = None
    base_price_cents: int
    currency: str
    unit_label: Optional[str] = None
    product_type: str
    min_quantity: int
    max_quantity: Optional[int] = None
    is_active: bool
    is_in_stock: bool
    preorder_only: bool
    prep_time_hours: int
    metadata: Optional[Dict[str, Any]] = None
    options: List[ProductOptionOut] = []
    model_config = ConfigDict(from_attributes=True)

class StoreSettingsOut(BaseModel):
    pickup_address: str
    pickup_instructions: str
    delivery_zones: List[str]
    delivery_fee_cents: int
    delivery_minimum_cents: int
    time_slots: List[str]
    payment_methods: List[str]
