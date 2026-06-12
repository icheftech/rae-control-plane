"""Connector Model - Registry Backbone (Phase 1)

NIST AI RMF MAP function: Define integration points for capabilities
Links capabilities to external systems, APIs, or infrastructure
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class ConnectorType(enum.Enum):
    """Integration point types"""
    API = "api"                # REST/GraphQL API endpoint
    DATABASE = "database"      # Database connection
    MESSAGE_QUEUE = "message_queue"  # Kafka, RabbitMQ, SQS
    S3_BUCKET = "s3_bucket"    # S3 or object storage
    ML_MODEL = "ml_model"      # Model serving endpoint
    LAMBDA = "lambda"          # Serverless function
    EXTERNAL_SERVICE = "external_service"  # Third-party service


class Connector(Base):
    """Integration connectors for capabilities
    
    Examples:
    - API connector to ML model serving endpoint
    - Database connector to PHI/PII data warehouse
    - S3 bucket connector for model artifacts
    - Lambda connector for async processing
    
    Security: Credentials NEVER stored in this model (use secrets manager)
    """
    __tablename__ = "connectors"

    # Primary identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connector_key = Column(String(255), unique=True, nullable=False, index=True)
    
    # Capability association
    capability_id = Column(UUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Connector details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    connector_type = Column(SQLEnum(ConnectorType), nullable=False)
    
    # Connection configuration (NO CREDENTIALS)
    # Use AWS Secrets Manager ARN or similar for credentials
    endpoint_url = Column(String(512), nullable=True)  # API/service endpoint
    config = Column(JSONB, nullable=True, default=dict)  # Type-specific config
    
    # Lifecycle
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Audit trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    capability = relationship("Capability", back_populates="connectors")

    def __repr__(self):
        return f"<Connector(key='{self.connector_key}', type={self.connector_type.value}, active={self.is_active})>"

    @property
    def full_key(self) -> str:
        """Composite key for audit trails"""
        return f"{self.capability.full_key}.{self.connector_key}"
    
    def validate_config(self) -> bool:
        """Type-specific config validation
        
        Override in subclasses or use Pydantic models
        """
        required_keys = {
            ConnectorType.API: ["method", "auth_type"],
            ConnectorType.DATABASE: ["db_type", "connection_string_secret_arn"],
            ConnectorType.ML_MODEL: ["model_name", "version"],
            # Add more as needed
        }
        
        if self.connector_type in required_keys:
            return all(k in (self.config or {}) for k in required_keys[self.connector_type])
        return True
