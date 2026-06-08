from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.inquiry import Inquiry
from app.schemas.inquiries import InquiryCreate, InquiryOut

router = APIRouter()

@router.post("", response_model=InquiryOut, status_code=status.HTTP_201_CREATED)
async def create_inquiry(payload: InquiryCreate, db: AsyncSession = Depends(get_db)):
    """Submit a contact form inquiry."""
    inquiry = Inquiry(
        full_name=payload.fullName,
        email=payload.email,
        phone=payload.phone,
        subject=payload.subject,
        message=payload.message,
        status="pending"
    )
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)
    return inquiry
