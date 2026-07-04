import json
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.order import Order
from app.services.payments import verify_webhook_signature

router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    # Read the raw body as bytes for signature verification
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")
    
    try:
        verification = verify_webhook_signature(payload, sig_header)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook verification failed: {str(e)}")
    
    if not verification.get("verified"):
        raise HTTPException(status_code=400, detail=f"Invalid Stripe signature: {verification.get('error')}")
        
    event = verification.get("event")
    
    # If stripe is installed and event was constructed successfully
    if event:
        # Convert to dict to safely use .get() as Stripe objects in newer SDKs do not support it directly
        event_dict = event.to_dict() if hasattr(event, "to_dict") else dict(event)
        
        event_type = event_dict.get('type')
        data_obj = event_dict.get('data', {}).get('object', {})
        
        # We stored the order_number in metadata when creating the payment intent/checkout session
        order_number = data_obj.get("metadata", {}).get("order_number")
        
        if order_number:
            result = await db.execute(select(Order).where(Order.order_number == order_number))
            order = result.scalar_one_or_none()
            if order:
                if event_type in ('payment_intent.succeeded', 'checkout.session.completed'):
                    order.payment_status = "paid"
                elif event_type in ('payment_intent.payment_failed', 'checkout.session.expired'):
                    order.payment_status = "failed"
                await db.commit()

    return {"status": "success"}
