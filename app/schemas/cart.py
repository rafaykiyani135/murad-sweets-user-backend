from typing import List, Optional
from pydantic import BaseModel, Field

class MixMatchSelection(BaseModel):
    id: str
    name: str
    quantity: int

class MixMatchBoxSchema(BaseModel):
    size: int
    price: float  # Price in dollars from client
    selectedItems: List[MixMatchSelection]

class AssortedSweet(BaseModel):
    name: str
    color: str

class AssortedBoxSchema(BaseModel):
    size: int
    price: float  # Price in dollars from client
    selectedItems: List[AssortedSweet]

class CartItemSchema(BaseModel):
    productId: str
    quantity: int
    name: Optional[str] = None
    mixMatch: Optional[MixMatchBoxSchema] = None
    assortedBox: Optional[AssortedBoxSchema] = None

class CartQuoteRequest(BaseModel):
    fulfillment: str  # "pickup" | "delivery"
    zip: Optional[str] = None
    items: List[CartItemSchema]

class CartQuoteResponse(BaseModel):
    subtotal_cents: int
    delivery_fee_cents: int
    tax_cents: int
    total_cents: int
    
    # Dollar helper conversions for frontend simplicity
    subtotal: float
    delivery_fee: float
    tax: float
    total: float
