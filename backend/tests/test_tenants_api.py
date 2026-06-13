"""Tenant API endpoint tests.

Proves the test client is using the isolated Testcontainers PostgreSQL
session (via the SAVEPOINT fixture), not the real DATABASE_URL.
"""
import pytest


class TestTenantAPI:
    """CRUD tests for /api/tenants endpoints."""

    def _create_tenant(self, client, **overrides):
        payload = {
            "tenant_name": "Acme Corp",
            "tenant_key": "acme_corp",
            "created_by": "test-harness",
            "is_active": True,
        }
        payload.update(overrides)
        return client.post("/api/tenants/", json=payload)

    def test_create_tenant(self, client):
        resp = self._create_tenant(client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["tenant_name"] == "Acme Corp"
        assert data["tenant_key"] == "acme_corp"
        assert data["created_by"] == "test-harness"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_tenant_duplicate_key(self, client):
        self._create_tenant(client, tenant_key="dup_key")
        resp = self._create_tenant(client, tenant_key="dup_key", tenant_name="Other")
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_list_tenants(self, client):
        self._create_tenant(client, tenant_key="list_a")
        self._create_tenant(client, tenant_key="list_b", tenant_name="Bravo")
        resp = client.get("/api/tenants/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        keys = {t["tenant_key"] for t in data}
        assert "list_a" in keys
        assert "list_b" in keys

    def test_get_tenant(self, client):
        create_resp = self._create_tenant(client, tenant_key="get_one")
        tenant_id = create_resp.json()["id"]
        resp = client.get(f"/api/tenants/{tenant_id}")
        assert resp.status_code == 200
        assert resp.json()["tenant_key"] == "get_one"

    def test_get_tenant_not_found(self, client):
        resp = client.get("/api/tenants/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_update_tenant(self, client):
        create_resp = self._create_tenant(client, tenant_key="update_me")
        tenant_id = create_resp.json()["id"]
        resp = client.patch(
            f"/api/tenants/{tenant_id}",
            json={"tenant_name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["tenant_name"] == "Updated Name"
        assert resp.json()["tenant_key"] == "update_me"

    def test_update_tenant_not_found(self, client):
        resp = client.patch(
            "/api/tenants/00000000-0000-0000-0000-000000000000",
            json={"tenant_name": "Ghost"},
        )
        assert resp.status_code == 404

    def test_delete_tenant(self, client):
        create_resp = self._create_tenant(client, tenant_key="delete_me")
        tenant_id = create_resp.json()["id"]
        resp = client.delete(f"/api/tenants/{tenant_id}")
        assert resp.status_code == 204
        get_resp = client.get(f"/api/tenants/{tenant_id}")
        assert get_resp.status_code == 404

    def test_delete_tenant_not_found(self, client):
        resp = client.delete("/api/tenants/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_isolation_between_tests(self, client):
        """Proves SAVEPOINT rollback: data from prior tests is not visible."""
        resp = client.get("/api/tenants/")
        assert resp.status_code == 200
        keys = {t["tenant_key"] for t in resp.json()}
        assert "acme_corp" not in keys, "Data from test_create_tenant leaked — SAVEPOINT rollback is broken"
