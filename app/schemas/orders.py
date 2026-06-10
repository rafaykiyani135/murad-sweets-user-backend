import uuid
from datetime import datetime, date
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.schemas.cart import CartItemSchema

class OrderCreate(BaseModel):
    fulfillment: str  # "pickup" | "delivery"
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    date: str  # YYYY-MM-DD
    slot: str  # "Morning" | "Afternoon" | "Evening"
    fullName: str
    email: EmailStr
    phone: str
    notes: Optional[str] = None
    paymentMethod: str  # "cod" | "card"
    items: List[CartItemSchema]

class OrderItemOut(BaseModel):
    id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    option_id: Optional[uuid.UUID] = None
    name_snapshot: str
    unit_price_cents: int
    unit_price: float
    quantity: int
    line_total_cents: int
    line_total: float
    selections: Optional[Any] = None
    
    model_config = ConfigDict(from_attributes=True)

class OrderContactInfo(BaseModel):
    fullName: str
    email: str
    phone: str
    notes: Optional[str] = None

class OrderOut(BaseModel):
    id: uuid.UUID
    order_number: str
    status: str
    fulfillment_type: str
    scheduled_date: str  # Formatted as YYYY-MM-DD
    scheduled_slot: str
    
    # Address details
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    
    # Financials
    subtotal_cents: int
    delivery_fee_cents: int
    tax_cents: int
    total_cents: int
    
    subtotal: float
    delivery_fee: float
    tax: float
    total: float
    
    # Payment details
    payment_method: str
    payment_status: str
    client_secret: Optional[str] = None  # Stripe client secret if card payment
    
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Mapped contact structure to align with frontend expectancies
    contact: OrderContactInfo
    items: List[OrderItemOut]
    
    model_config = ConfigDict(from_attributes=True)

# Admin Status updates
class OrderStatusUpdate(BaseModel):
    status: str

# Admin Notes updates
class OrderNotesUpdate(BaseModel):
    admin_notes: str

# Lightweight summary for history/dashboard listing
class OrderSummary(BaseModel):
    order_number: str
    status: str
    customer_name: str
    total: float
    scheduled_date: str
    item_count: int
    fulfillment_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
