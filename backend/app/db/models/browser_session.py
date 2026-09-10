from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class BrowserSession(Base):
    __tablename__ = 'browser_sessions'
    token_hash = Column(String(64), primary_key=True)
    subject = Column(String(255), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
