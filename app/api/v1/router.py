from fastapi import APIRouter
from app.api.v1 import catalog, cart, orders, inquiries, admin, history, settings, products_admin

api_router = APIRouter()

# Register sub-routers with correct prefixes and tags
api_router.include_router(catalog.router, tags=["Catalog"])
api_router.include_router(cart.router, prefix="/cart", tags=["Cart"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(inquiries.router, prefix="/contact-inquiries", tags=["Inquiries"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(history.router, prefix="/history", tags=["History"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(products_admin.router, prefix="/admin/products", tags=["Products Admin"])
