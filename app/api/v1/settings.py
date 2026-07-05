from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.setting import AppSetting
from app.models.admin_user import AdminUser
from app.schemas.setting import SettingOut, SettingUpdate
from app.api.v1.auth import get_current_admin_from_cookie

router = APIRouter()

@router.get("/{key}", response_model=SettingOut)
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a setting by key. If it doesn't exist, provide a default for known keys."""
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        # Provide defaults for known keys
        if key == "delivery_fee_per_mile":
            setting = AppSetting(key=key, value="1.00", description="Delivery fee per mile in dollars.")
            db.add(setting)
            await db.commit()
            await db.refresh(setting)
        else:
            raise HTTPException(status_code=404, detail="Setting not found")
            
    return setting

@router.put("/{key}", response_model=SettingOut)
async def update_setting(key: str, payload: SettingUpdate, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin_from_cookie)):
    """Create or update a setting by key."""
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = payload.value
        if payload.description is not None:
            setting.description = payload.description
    else:
        setting = AppSetting(key=key, value=payload.value, description=payload.description)
        db.add(setting)
        
    await db.commit()
    await db.refresh(setting)
    return setting
