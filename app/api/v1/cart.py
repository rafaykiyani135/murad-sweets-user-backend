from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.cart import CartQuoteRequest, CartQuoteResponse
from app.services.pricing import calculate_quote

router = APIRouter()

@router.post("/quote", response_model=CartQuoteResponse)
async def get_cart_quote(payload: CartQuoteRequest, db: AsyncSession = Depends(get_db)):
    """
    Validate cart items and return trusted subtotal, delivery fee, and grand total.
    Ensures pricing is computed server-side and delivery zones/minimums are respected.
    """
    items_list = [item.model_dump() for item in payload.items]
    
    quote = await calculate_quote(
        db=db,
        items=items_list,
        fulfillment_type=payload.fulfillment,
        zip_code=payload.zip
    )
    
    # Dollar representations for the frontend
    subtotal = quote["subtotal_cents"] / 100.0
    delivery_fee = quote["delivery_fee_cents"] / 100.0
    tax = quote["tax_cents"] / 100.0
    total = quote["total_cents"] / 100.0

    return CartQuoteResponse(
        subtotal_cents=quote["subtotal_cents"],
        delivery_fee_cents=quote["delivery_fee_cents"],
        tax_cents=quote["tax_cents"],
        total_cents=quote["total_cents"],
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        tax=tax,
        total=total
    )
