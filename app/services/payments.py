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
    Falls back to a mock intent if Stripe is not installed or keys are missing.
    """
    if stripe is None or not settings.STRIPE_SECRET_KEY:
        # Return mock intent details for local testing
        return {
            "client_secret": f"pi_mock_secret_for_{order_number}_{amount_cents}",
            "id": f"pi_mock_{order_number}",
            "amount": amount_cents,
            "currency": currency,
            "status": "requires_payment_method",
            "is_mock": True
        }

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
        # fallback to mock
        return {
            "client_secret": f"pi_mock_fallback_secret_for_{order_number}_{amount_cents}",
            "id": f"pi_mock_fallback_{order_number}",
            "amount": amount_cents,
            "currency": currency,
            "status": "requires_payment_method",
            "is_mock": True
        }

def verify_webhook_signature(payload: str, sig_header: str) -> dict:
    """
    Verifies the webhook signature sent by Stripe.
    """
    if stripe is None or not settings.STRIPE_WEBHOOK_SECRET or not settings.STRIPE_SECRET_KEY:
        # Mock webhook processing
        return {"type": "mock", "verified": True}
        
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return {"type": "stripe", "verified": True, "event": event}
    except Exception as e:
        print(f"Stripe Webhook verification failed: {e}")
        return {"type": "stripe", "verified": False, "error": str(e)}
