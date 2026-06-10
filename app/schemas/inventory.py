import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict


class StockSummary(BaseModel):
    """Lightweight snapshot of a tracked product's current inventory status."""
    product_id: uuid.UUID
    slug: str
    name: str
    category: str
    product_type: str
    quantity_on_hand: int  # Never None — endpoint only returns tracked products
    is_in_stock: bool

    model_config = ConfigDict(from_attributes=True)
