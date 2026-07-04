from app.core.config import settings

try:
    import stripe
    if settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
except ImportError:
    stripe = None

def create_payment_intent(amount_cents: int, currency: str = "usd", order_number: str = "") -> dict:
    """
    Creates a Stripe PaymentIntent for frontend Elements integration.
    """
    if stripe is None or not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe is not configured or keys are missing.")

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency,
            metadata={"order_number": order_number}
        )
        return {
            "client_secret": intent.client_secret,
            "id": intent.id,
            "amount": intent.amount,
            "currency": intent.currency,
            "status": intent.status,
            "is_mock": False
        }
    except Exception as e:
        print(f"Stripe PaymentIntent creation failed: {e}")
        raise

def create_checkout_session(amount_cents: int, currency: str = "usd", order_number: str = "", customer_email: str = "", frontend_url: str = None) -> dict:
    """
    Creates a Stripe Checkout Session for official Stripe redirect flow.
    """
    base_url = frontend_url or settings.FRONTEND_ORIGIN

    if stripe is None or not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe is not configured or keys are missing.")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': {
                        'name': f"Order #{order_number} - Murad Sweets",
                    },
                    'unit_amount': amount_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{base_url}/order-confirmation/{order_number}?success=true",
            cancel_url=f"{base_url}/checkout",
            payment_intent_data={
                'metadata': {'order_number': order_number}
            },
            metadata={"order_number": order_number},
            customer_email=customer_email or None,
        )
        return {
            "checkout_url": session.url,
            "id": session.id,
            "status": session.status,
            "is_mock": False
        }
    except Exception as e:
        print(f"Stripe Checkout Session creation failed: {e}")
        raise

def verify_webhook_signature(payload: str, sig_header: str) -> dict:
    """
    Verifies the webhook signature sent by Stripe.
    """
    if stripe is None or not settings.STRIPE_WEBHOOK_SECRET or not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe signature verification failed: Stripe credentials not configured.")
        
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return {"type": "stripe", "verified": True, "event": event}
    except Exception as e:
        print(f"Stripe Webhook verification failed: {e}")
        return {"type": "stripe", "verified": False, "error": str(e)}

def check_payment_intent_status(order_number: str) -> str | None:
    """
    Search for a Stripe PaymentIntent for the given order number and return its status.
    Returns None if Stripe is not configured, or if no intent is found.
    """
    if stripe is None or not settings.STRIPE_SECRET_KEY:
        return None

    try:
        res = stripe.PaymentIntent.search(query=f"metadata['order_number']:'{order_number}'")
        if res.data:
            # Get the first matching intent
            intent = res.data[0]
            return intent.status
    except Exception as e:
        print(f"Stripe PaymentIntent search failed: {e}")
    
    return None

