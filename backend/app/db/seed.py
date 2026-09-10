"""Database Seeding Script

Populates the database with demo data for testing and demonstration.
Creates example workflows, capabilities, connectors, control policies,
kill switches, and break glass access records.

Usage:
    python -m app.db.seed

WARNING: This will add demo data to the database. Do not run in production.
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_maker, init_db
from app.db.models.workflow import Workflow
from app.db.models.capability import Capability, RiskLevel
from app.db.models.connector import Connector, ConnectorType
from app.db.models.control_policy import ControlPolicy, PolicyOutcome
from app.db.models.kill_switch import KillSwitch, KillSwitchMode, KillSwitchScope
from app.db.models.break_glass import BreakGlass


async def seed_database():
    """Seed database with demo data."""
    print("🌱 Starting database seeding...")
    
    async with async_session_maker() as db:
        # Create workflows
        print("📋 Creating workflows...")
        workflows = [
            Workflow(
                name="PHI Data Analysis Workflow",
                description="HIPAA-compliant patient data analysis pipeline",
                requires_approval=True,
                approval_stages=["data_officer", "security_team"],
                metadata={
                    "compliance": ["HIPAA", "SOC2"],
                    "data_classification": "PHI",
                },
            ),
            Workflow(
                name="Production Database Migration",
                description="Multi-stage production database schema migration",
                requires_approval=True,
                approval_stages=["dba", "tech_lead", "cto"],
                metadata={
                    "risk_level": "critical",
                    "rollback_plan": "automated",
                },
            ),
            Workflow(
                name="Customer Support Bot",
                description="AI-powered customer inquiry handler",
                requires_approval=False,
                approval_stages=[],
                metadata={"customer_facing": True},
            ),
        ]
        
        for workflow in workflows:
            db.add(workflow)
        
        # Create capabilities
        print("⚡ Creating capabilities...")
        capabilities = [
            Capability(
                name="Read Patient Records",
                description="Query patient medical records from EHR system",
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
                max_concurrency=5,
                timeout_seconds=30,
                allowed_environments=["prod"],
                constraints={"phi_access": True, "audit_required": True},
            ),
            Capability(
                name="Send Email Notification",
                description="Send transactional emails to users",
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                max_concurrency=100,
                timeout_seconds=10,
                allowed_environments=["dev", "staging", "prod"],
                constraints={"rate_limit": 1000},
            ),
            Capability(
                name="Execute Database Migration",
                description="Run schema migration on production database",
                risk_level=RiskLevel.CRITICAL,
                requires_approval=True,
                max_concurrency=1,
                timeout_seconds=300,
                allowed_environments=["prod"],
                constraints={"backup_required": True, "maintenance_window": True},
            ),
            Capability(
                name="Write Audit Log",
                description="Append to immutable audit trail",
                risk_level=RiskLevel.MEDIUM,
                requires_approval=False,
                max_concurrency=1000,
                timeout_seconds=5,
                allowed_environments=["dev", "staging", "prod"],
                constraints={"hash_chain": True},
            ),
        ]
        
        for capability in capabilities:
            db.add(capability)
        
        # Create connectors
        print("🔌 Creating connectors...")
        connectors = [
            Connector(
                name="Production PostgreSQL",
                description="Primary production database cluster",
                connector_type=ConnectorType.DATABASE,
                endpoint_url="postgresql://prod-db.internal:5432/app",
                requires_auth=True,
                config={"ssl_mode": "require", "pool_size": 20},
                credentials={"encrypted": "demo_encrypted_credentials"},
                metadata={"region": "us-east-1"},
            ),
            Connector(
                name="SendGrid Email Service",
                description="Transactional email provider",
                connector_type=ConnectorType.API,
                endpoint_url="https://api.sendgrid.com/v3",
                requires_auth=True,
                config={"timeout": 30},
                credentials={"api_key": "encrypted_sendgrid_key"},
            ),
            Connector(
                name="S3 Document Storage",
                description="AWS S3 bucket for document storage",
                connector_type=ConnectorType.STORAGE,
                endpoint_url="s3://prod-documents",
                requires_auth=True,
                config={"region": "us-west-2"},
                credentials={"aws_key_id": "encrypted", "aws_secret": "encrypted"},
            ),
        ]
        
        for connector in connectors:
            db.add(connector)
        
        # Create control policies
        print("🛡️  Creating control policies...")
        policies = [
            ControlPolicy(
                name="Production Write Restriction",
                description="Require approval for all production write operations",
                outcome=PolicyOutcome.REVIEW,
                conditions={
                    "environment": "prod",
                    "operation_type": "write",
                },
                metadata={"priority": "high"},
            ),
            ControlPolicy(
                name="PHI Access Logging",
                description="Mandatory audit logging for PHI data access",
                outcome=PolicyOutcome.ALLOW,
                conditions={"data_classification": "PHI"},
                metadata={"audit_required": True},
            ),
            ControlPolicy(
                name="Block Unencrypted Transmission",
                description="Deny operations without TLS/encryption",
                outcome=PolicyOutcome.DENY,
                conditions={"encryption": False},
                metadata={"compliance": "SOC2"},
            ),
        ]
        
        for policy in policies:
            db.add(policy)
        
        # Create kill switches
        print("🚨 Creating kill switches...")
        kill_switches = [
            KillSwitch(
                name="Emergency Production Freeze",
                description="Stop all production writes during incident",
                mode=KillSwitchMode.HARD_STOP,
                scope=KillSwitchScope.ENVIRONMENT,
                scope_identifiers=["prod"],
                is_active=False,
                reason="Available for emergency use",
                metadata={"severity": "critical"},
            ),
            KillSwitch(
                name="PHI Access Suspension",
                description="Temporarily disable PHI data access",
                mode=KillSwitchMode.DEGRADE,
                scope=KillSwitchScope.CAPABILITY,
                scope_identifiers=["read_patient_records"],
                is_active=False,
                reason="Available for compliance incidents",
            ),
        ]
        
        for ks in kill_switches:
            db.add(ks)
        
        # Create break glass access
        print("🔓 Creating break glass records...")
        break_glass = [
            BreakGlass(
                reason="Production outage - database recovery required",
                granted_by="admin@example.com",
                granted_to="sre-team@example.com",
                expires_at=datetime.utcnow() + timedelta(hours=2),
                capabilities_granted=["execute_database_migration"],
                metadata={"incident_id": "INC-12345"},
            ),
        ]
        
        for bg in break_glass:
            db.add(bg)
        
        await db.commit()
    
    print("✅ Database seeding completed!")
    print("\n📊 Summary:")
    print(f"  - {len(workflows)} workflows")
    print(f"  - {len(capabilities)} capabilities")
    print(f"  - {len(connectors)} connectors")
    print(f"  - {len(policies)} control policies")
    print(f"  - {len(kill_switches)} kill switches")
    print(f"  - {len(break_glass)} break glass records")
    print("\n🎯 Ready for testing and demonstration!\n")


if __name__ == "__main__":
    asyncio.run(seed_database())
