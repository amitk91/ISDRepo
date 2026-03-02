"""
JSON schema validation for SDLC service request webhook payloads.
"""
from __future__ import annotations

from typing import Any

import jsonschema
from jsonschema import ValidationError

# ── Supported request types ────────────────────────────────────────────────────

REQUEST_TYPES = {
    "environment_provisioning",
    "identity_access",
    "network_connectivity",
    "platform_services",
    "security_exception",
}

# ── Base schema (all request types) ───────────────────────────────────────────

BASE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["request_type", "application_name", "submitted_by", "timestamp", "data"],
    "additionalProperties": False,
    "properties": {
        "request_type": {
            "type": "string",
            "enum": sorted(REQUEST_TYPES),
        },
        "application_name": {"type": "string", "minLength": 1},
        "submitted_by": {"type": "string", "format": "email"},
        "timestamp": {"type": "string", "minLength": 1},
        "data": {"type": "object"},
    },
}

# ── Per-type data schemas ──────────────────────────────────────────────────────

DATA_SCHEMAS: dict[str, dict[str, Any]] = {
    "environment_provisioning": {
        "type": "object",
        "required": [
            "business_owner",
            "technical_owner",
            "cost_center",
            "environment_type",
            "region",
            "data_classification",
            "criticality_tier",
            "internet_exposure",
            "rto",
            "rpo",
            "expected_go_live_date",
        ],
        "properties": {
            "business_owner": {"type": "string", "minLength": 1},
            "technical_owner": {"type": "string", "minLength": 1},
            "cost_center": {"type": "string", "minLength": 1},
            "environment_type": {
                "type": "string",
                "enum": ["Sandbox", "Dev", "UAT"],
            },
            "region": {"type": "string", "minLength": 1},
            "data_classification": {
                "type": "string",
                "enum": ["Public", "Confidential", "Restricted"],
            },
            "criticality_tier": {
                "type": "string",
                "enum": ["Tier 1", "Tier 2", "Tier 3"],
            },
            "internet_exposure": {"type": "boolean"},
            "rto": {"type": "string", "minLength": 1},
            "rpo": {"type": "string", "minLength": 1},
            "cfd_reference_id": {"type": "string"},
            "expected_go_live_date": {
                "type": "string",
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
            },
            "notes": {"type": "string"},
        },
    },
    "identity_access": {
        "type": "object",
        "required": [
            "identity_type",
            "scope",
            "role_requested",
            "temporary_access",
            "business_justification",
        ],
        "properties": {
            "identity_type": {
                "type": "string",
                "enum": ["Managed Identity", "Service Principal"],
            },
            "scope": {
                "type": "string",
                "enum": ["Subscription", "Resource Group"],
            },
            "role_requested": {"type": "string", "minLength": 1},
            "temporary_access": {"type": "boolean"},
            "duration": {"type": "string"},
            "business_justification": {"type": "string", "minLength": 1},
        },
    },
    "network_connectivity": {
        "type": "object",
        "required": [
            "connectivity_type",
            "source",
            "destination",
            "protocol_port",
            "public_exposure",
            "third_party_integration",
        ],
        "properties": {
            "connectivity_type": {
                "type": "string",
                "enum": ["Private Endpoint", "Firewall Rule", "API Exposure"],
            },
            "source": {"type": "string", "minLength": 1},
            "destination": {"type": "string", "minLength": 1},
            "protocol_port": {"type": "string", "minLength": 1},
            "public_exposure": {"type": "boolean"},
            "third_party_integration": {"type": "boolean"},
        },
    },
    "platform_services": {
        "type": "object",
        "required": [
            "service_type",
            "sku",
            "estimated_monthly_cost_usd",
            "backup_required",
            "monitoring_required",
        ],
        "properties": {
            "service_type": {
                "type": "string",
                "enum": ["Database", "Storage", "Queue", "Cache", "AI/ML"],
            },
            "sku": {
                "type": "string",
                "enum": ["Standard", "Premium", "Custom"],
            },
            "estimated_monthly_cost_usd": {"type": "number", "minimum": 0},
            "backup_required": {"type": "boolean"},
            "monitoring_required": {"type": "boolean"},
        },
    },
    "security_exception": {
        "type": "object",
        "required": [
            "policy_control_violated",
            "business_justification",
            "compensating_controls",
            "expiry_date",
            "risk_acknowledged",
        ],
        "properties": {
            "policy_control_violated": {"type": "string", "minLength": 1},
            "business_justification": {"type": "string", "minLength": 1},
            "compensating_controls": {"type": "string", "minLength": 1},
            "expiry_date": {
                "type": "string",
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
            },
            "risk_acknowledged": {"type": "boolean", "const": True},
        },
    },
}


# ── Public API ─────────────────────────────────────────────────────────────────

class SchemaValidationError(ValueError):
    """Raised when the webhook payload fails JSON schema validation."""


def validate_payload(payload: dict[str, Any]) -> None:
    """
    Validate a webhook payload against the base schema and the per-type data schema.

    Raises SchemaValidationError with a human-readable message on failure.
    """
    # 1. Base schema
    try:
        jsonschema.validate(instance=payload, schema=BASE_SCHEMA)
    except ValidationError as exc:
        raise SchemaValidationError(f"Base schema validation failed: {exc.message}") from exc

    # 2. Per-type data schema
    request_type = payload["request_type"]
    data_schema = DATA_SCHEMAS.get(request_type)
    if data_schema is None:
        raise SchemaValidationError(f"Unknown request_type: '{request_type}'")

    try:
        jsonschema.validate(instance=payload["data"], schema=data_schema)
    except ValidationError as exc:
        raise SchemaValidationError(
            f"Data schema validation failed for '{request_type}': {exc.message}"
        ) from exc
