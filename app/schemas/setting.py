from pydantic import BaseModel, ConfigDict
from typing import Optional

class SettingBase(BaseModel):
    value: str
    description: Optional[str] = None

class SettingUpdate(SettingBase):
    pass

class SettingOut(SettingBase):
    key: str
    model_config = ConfigDict(from_attributes=True)
