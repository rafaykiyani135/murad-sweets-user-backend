from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.base import Base
from app.db.session import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions: Import all models to register them on Base.metadata
    from app.models.category import Category
    from app.models.product import Product, ProductOption, CustomBoxRule
    from app.models.customer import Customer
    from app.models.order import Order, OrderItem
    from app.models.inquiry import Inquiry
    from app.models.admin_user import AdminUser
    from app.models.setting import AppSetting
    
    # Auto-create tables for development convenience
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield
    # Shutdown actions (if any)

app = FastAPI(
    title="Murad Sweets API",
    description="Python FastAPI backend serving as the single source of truth for the Murad Sweets application.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration — fully driven by .env CORS_ORIGINS and FRONTEND_ORIGIN
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "app": "Murad Sweets API",
        "documentation": "/docs"
    }

# Register all API endpoints
app.include_router(api_router, prefix="/api/v1")
