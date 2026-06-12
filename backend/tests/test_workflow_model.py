"""Unit tests for Workflow model

Demonstrates testing patterns for S.S.O. Control Plane models:
- Model creation and validation
- Relationships and foreign keys
- Business logic methods
- Database constraints
"""
import pytest
from datetime import datetime
from app.db.models.workflow import Workflow


@pytest.mark.unit
@pytest.mark.models
class TestWorkflowModel:
    """Test suite for Workflow model."""

    def test_create_workflow(self, test_db, sample_workflow_data):
        """Test creating a basic workflow."""
        workflow = Workflow(**sample_workflow_data)
        test_db.add(workflow)
        test_db.commit()
        test_db.refresh(workflow)

        assert workflow.id is not None
        assert workflow.name == sample_workflow_data["name"]
        assert workflow.version == sample_workflow_data["version"]
        assert workflow.is_active is True
        assert workflow.created_at is not None
        assert workflow.updated_at is not None

    def test_workflow_name_required(self, test_db):
        """Test that workflow name is required."""
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            workflow = Workflow(
                description="Test without name",
                version="1.0.0"
            )
            test_db.add(workflow)
            test_db.commit()

    def test_workflow_version_required(self, test_db, sample_workflow_data):
        """Test that version is required."""
        data = sample_workflow_data.copy()
        del data["version"]
        
        with pytest.raises(Exception):
            workflow = Workflow(**data)
            test_db.add(workflow)
            test_db.commit()

    def test_workflow_unique_name_version(self, test_db, sample_workflow_data):
        """Test that name+version combination must be unique."""
        # Create first workflow
        workflow1 = Workflow(**sample_workflow_data)
        test_db.add(workflow1)
        test_db.commit()

        # Attempt to create duplicate
        with pytest.raises(Exception):  # IntegrityError on unique constraint
            workflow2 = Workflow(**sample_workflow_data)
            test_db.add(workflow2)
            test_db.commit()

    def test_workflow_soft_delete(self, test_db, sample_workflow_data):
        """Test soft delete pattern (is_active=False)."""
        workflow = Workflow(**sample_workflow_data)
        test_db.add(workflow)
        test_db.commit()

        # Soft delete
        workflow.is_active = False
        test_db.commit()
        test_db.refresh(workflow)

        assert workflow.is_active is False
        assert workflow.id is not None  # Still exists in DB

    def test_workflow_timestamps(self, test_db, sample_workflow_data):
        """Test automatic timestamp management."""
        workflow = Workflow(**sample_workflow_data)
        test_db.add(workflow)
        test_db.commit()
        test_db.refresh(workflow)

        created = workflow.created_at
        updated = workflow.updated_at

        assert created is not None
        assert updated is not None
        assert created == updated  # Same on creation

        # Update workflow
        workflow.description = "Updated description"
        test_db.commit()
        test_db.refresh(workflow)

        assert workflow.updated_at > updated  # Updated timestamp changed
        assert workflow.created_at == created  # Created timestamp unchanged

    def test_workflow_metadata_json(self, test_db, sample_workflow_data):
        """Test JSON metadata field."""
        sample_workflow_data["metadata"] = {
            "author": "test-user",
            "tags": ["production", "critical"],
            "complexity": "high"
        }
        
        workflow = Workflow(**sample_workflow_data)
        test_db.add(workflow)
        test_db.commit()
        test_db.refresh(workflow)

        assert workflow.metadata["author"] == "test-user"
        assert len(workflow.metadata["tags"]) == 2
        assert workflow.metadata["complexity"] == "high"
