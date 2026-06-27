from sqlalchemy import Column, String
from app.db.base import Base

class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)
    description = Column(String, nullable=True)
