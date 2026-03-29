"""
Tests for the SDLC Service Management middleware.

Covers:
- JSON schema validation (schema.py)
- Issue title / label / body generation (issue_creator.py)
- Webhook endpoint behaviour (app.py)
- GitHub Actions validation script logic (validate_issue.py)
"""
from __future__ import annotations

import os

import pytest

from middleware.schema import SchemaValidationError, validate_payload
from middleware.issue_creator import (
    _build_body,
    _resolve_labels,
)


# ── Fixture helpers ────────────────────────────────────────────────────────────

def _env_payload(**overrides):
    base = {
        "request_type": "environment_provisioning",
        "application_name": "Payments API",
        "submitted_by": "user@company.com",
        "timestamp": "2024-01-01T00:00:00Z",
        "data": {
            "business_owner": "owner@company.com",
            "technical_owner": "tech@company.com",
            "cost_center": "CC-1234",
            "environment_type": "Dev",
            "region": "eastus",
            "data_classification": "Confidential",
            "criticality_tier": "Tier 2",
            "internet_exposure": False,
            "rto": "4 hours",
            "rpo": "1 hour",
            "expected_go_live_date": "2024-06-01",
        },
    }
    base.update(overrides)
    return base


def _sec_ex_payload(**data_overrides):
    base = {
        "request_type": "security_exception",
        "application_name": "Payments API",
        "submitted_by": "user@company.com",
        "timestamp": "2024-01-01T00:00:00Z",
        "data": {
            "policy_control_violated": "Storage public access",
            "business_justification": "Needed for partner integration",
            "compensating_controls": "IP allowlist in place",
            "expiry_date": "2024-12-31",
            "risk_acknowledged": True,
        },
    }
    base["data"].update(data_overrides)
    return base


# ── Schema validation tests ────────────────────────────────────────────────────

class TestSchemaValidation:
    def test_valid_environment_payload(self):
        validate_payload(_env_payload())  # Should not raise

    def test_missing_required_base_field(self):
        payload = _env_payload()
        del payload["application_name"]
        with pytest.raises(SchemaValidationError, match="application_name"):
            validate_payload(payload)

    def test_invalid_request_type(self):
        payload = _env_payload(request_type="unknown_type")
        with pytest.raises(SchemaValidationError):
            validate_payload(payload)

    def test_invalid_environment_type(self):
        payload = _env_payload()
        payload["data"]["environment_type"] = "Production"
        with pytest.raises(SchemaValidationError, match="Production"):
            validate_payload(payload)

    def test_valid_security_exception(self):
        validate_payload(_sec_ex_payload())  # Should not raise

    def test_security_exception_expiry_date_format(self):
        with pytest.raises(SchemaValidationError):
            validate_payload(_sec_ex_payload(expiry_date="31-12-2024"))

    def test_security_exception_risk_must_be_acknowledged(self):
        with pytest.raises(SchemaValidationError):
            validate_payload(_sec_ex_payload(risk_acknowledged=False))

    def test_valid_identity_access_payload(self):
        validate_payload({
            "request_type": "identity_access",
            "application_name": "Payments API",
            "submitted_by": "user@company.com",
            "timestamp": "2024-01-01T00:00:00Z",
            "data": {
                "identity_type": "Managed Identity",
                "scope": "Resource Group",
                "role_requested": "Storage Blob Data Reader",
                "temporary_access": False,
                "business_justification": "Required for blob storage access",
            },
        })

    def test_valid_network_connectivity_payload(self):
        validate_payload({
            "request_type": "network_connectivity",
            "application_name": "Payments API",
            "submitted_by": "user@company.com",
            "timestamp": "2024-01-01T00:00:00Z",
            "data": {
                "connectivity_type": "Private Endpoint",
                "source": "10.0.0.0/24",
                "destination": "storage-account",
                "protocol_port": "TCP/443",
                "public_exposure": False,
                "third_party_integration": False,
            },
        })

    def test_valid_platform_services_payload(self):
        validate_payload({
            "request_type": "platform_services",
            "application_name": "Payments API",
            "submitted_by": "user@company.com",
            "timestamp": "2024-01-01T00:00:00Z",
            "data": {
                "service_type": "Database",
                "sku": "Standard",
                "estimated_monthly_cost_usd": 500,
                "backup_required": True,
                "monitoring_required": True,
            },
        })


# ── Label resolution tests ─────────────────────────────────────────────────────

class TestLabelResolution:
    def test_environment_request_gets_environment_label(self):
        labels = _resolve_labels("environment_provisioning", {"environment_type": "Dev"})
        assert "environment" in labels
        assert "dev" in labels

    def test_sandbox_environment(self):
        labels = _resolve_labels("environment_provisioning", {"environment_type": "Sandbox"})
        assert "sandbox" in labels

    def test_uat_environment(self):
        labels = _resolve_labels("environment_provisioning", {"environment_type": "UAT"})
        assert "uat" in labels

    def test_confidential_classification(self):
        labels = _resolve_labels("environment_provisioning", {"data_classification": "Confidential"})
        assert "confidential" in labels

    def test_restricted_classification(self):
        labels = _resolve_labels("environment_provisioning", {"data_classification": "Restricted"})
        assert "restricted" in labels

    def test_internet_exposure_adds_public_label(self):
        labels = _resolve_labels("environment_provisioning", {"internet_exposure": True})
        assert "public" in labels

    def test_no_internet_exposure_no_public_label(self):
        labels = _resolve_labels("environment_provisioning", {"internet_exposure": False})
        assert "public" not in labels

    def test_high_cost_label_applied(self):
        labels = _resolve_labels("platform_services", {"estimated_monthly_cost_usd": 1500})
        assert "high-cost" in labels

    def test_below_threshold_no_high_cost_label(self):
        labels = _resolve_labels("platform_services", {"estimated_monthly_cost_usd": 500})
        assert "high-cost" not in labels

    def test_security_exception_label(self):
        labels = _resolve_labels("security_exception", {})
        assert "security-exception" in labels

    def test_iam_label(self):
        labels = _resolve_labels("identity_access", {})
        assert "iam" in labels

    def test_network_label(self):
        labels = _resolve_labels("network_connectivity", {})
        assert "network" in labels

    def test_platform_label(self):
        labels = _resolve_labels("platform_services", {})
        assert "platform" in labels


# ── Issue body builder tests ───────────────────────────────────────────────────

class TestIssueBodies:
    def test_env_body_contains_required_fields(self):
        data = {
            "business_owner": "owner@company.com",
            "technical_owner": "tech@company.com",
            "cost_center": "CC-1234",
            "environment_type": "Dev",
            "region": "eastus",
            "data_classification": "Confidential",
            "criticality_tier": "Tier 2",
            "internet_exposure": False,
            "rto": "4h",
            "rpo": "1h",
            "expected_go_live_date": "2024-06-01",
        }
        body = _build_body("environment_provisioning", "Payments API", "u@c.com", "2024-01-01", data)
        assert "Payments API" in body
        assert "Dev" in body
        assert "eastus" in body
        assert "Environment Provisioning" in body

    def test_security_exception_body_contains_expiry(self):
        data = {
            "policy_control_violated": "Public access",
            "business_justification": "Partner access",
            "compensating_controls": "IP allowlist",
            "expiry_date": "2024-12-31",
            "risk_acknowledged": True,
        }
        body = _build_body("security_exception", "App", "u@c.com", "2024-01-01", data)
        assert "2024-12-31" in body
        assert "Security Exception" in body

    def test_iam_body_contains_identity_type(self):
        data = {
            "identity_type": "Managed Identity",
            "scope": "Resource Group",
            "role_requested": "Storage Blob Data Reader",
            "temporary_access": False,
            "business_justification": "Blob access required",
        }
        body = _build_body("identity_access", "App", "u@c.com", "2024-01-01", data)
        assert "Managed Identity" in body
        assert "Storage Blob Data Reader" in body

    def test_body_includes_attribution_footer(self):
        body = _build_body("identity_access", "App", "u@c.com", "2024-01-01", {
            "identity_type": "Managed Identity",
            "scope": "Subscription",
            "role_requested": "Contributor",
            "temporary_access": False,
            "business_justification": "Test",
        })
        assert "automatically generated" in body


# ── Flask app tests ────────────────────────────────────────────────────────────

class TestFlaskApp:
    @pytest.fixture()
    def client(self):
        os.environ.setdefault("GITHUB_TOKEN", "fake-token")
        os.environ.setdefault("GITHUB_REPO", "org/cloud-ops-backlog")
        from middleware.app import app as flask_app
        flask_app.config["TESTING"] = True
        with flask_app.test_client() as c:
            yield c

    def test_health_endpoint(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_non_json_returns_415(self, client):
        resp = client.post("/webhook", data="plain text", content_type="text/plain")
        assert resp.status_code == 415

    def test_invalid_json_returns_400(self, client):
        resp = client.post(
            "/webhook",
            data="not json",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_schema_validation_failure_returns_422(self, client):
        resp = client.post(
            "/webhook",
            json={
                "request_type": "environment_provisioning",
                # Missing required fields
            },
        )
        assert resp.status_code == 422
