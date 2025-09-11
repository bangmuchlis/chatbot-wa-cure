from sqlalchemy import Column, Integer, String, LargeBinary, DateTime
from sqlalchemy.sql import func
from app.entities.base import Base

class ImageDocument(Base):
    __tablename__ = "image"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True) 
    description = Column(String, nullable=True)  
    file_data = Column(LargeBinary, nullable=False)  
    media_id = Column(String, nullable=True, index=True)  
    file_extension = Column(String, nullable=True) 
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
