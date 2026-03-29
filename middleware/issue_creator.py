"""
GitHub Issue creator for SDLC service requests.

Maps validated webhook payloads to GitHub Issues with:
- Standardised title convention
- Label taxonomy
- Structured Markdown issue body
"""
from __future__ import annotations

from typing import Any

from github import Github

# ── Constants ──────────────────────────────────────────────────────────────────

HIGH_COST_THRESHOLD_USD = 1000

_TITLE_TEMPLATES: dict[str, str] = {
    "environment_provisioning": "ENV | {application_name} | {region}",
    "identity_access": "IAM | {application_name}",
    "network_connectivity": "NET | {application_name}",
    "platform_services": "PLAT | {application_name}",
    "security_exception": "SEC-EX | {application_name}",
}

_REQUEST_TYPE_LABELS: dict[str, str] = {
    "environment_provisioning": "environment",
    "identity_access": "iam",
    "network_connectivity": "network",
    "platform_services": "platform",
    "security_exception": "security-exception",
}

_DATA_CLASSIFICATION_LABELS: dict[str, str] = {
    "Public": "public",
    "Confidential": "confidential",
    "Restricted": "restricted",
}

_ENVIRONMENT_LABELS: dict[str, str] = {
    "Sandbox": "sandbox",
    "Dev": "dev",
    "UAT": "uat",
}


# ── Label resolution ───────────────────────────────────────────────────────────

def _resolve_labels(request_type: str, data: dict[str, Any]) -> list[str]:
    """Return the list of labels to apply based on request type and data fields."""
    labels: list[str] = [_REQUEST_TYPE_LABELS[request_type]]

    # Environment label
    env_type = data.get("environment_type", "")
    if env_type in _ENVIRONMENT_LABELS:
        labels.append(_ENVIRONMENT_LABELS[env_type])

    # Data classification / risk
    classification = data.get("data_classification", "")
    if classification in _DATA_CLASSIFICATION_LABELS:
        labels.append(_DATA_CLASSIFICATION_LABELS[classification])

    # Internet / public exposure
    if data.get("internet_exposure") or data.get("public_exposure"):
        if "public" not in labels:
            labels.append("public")

    # High cost
    cost = data.get("estimated_monthly_cost_usd")
    if isinstance(cost, (int, float)) and cost >= HIGH_COST_THRESHOLD_USD:
        labels.append("high-cost")

    return labels


# ── Issue body builders ────────────────────────────────────────────────────────

def _bool_str(value: Any) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value) if value is not None else "—"


def _build_body(
    request_type: str,
    application_name: str,
    submitted_by: str,
    timestamp: str,
    data: dict[str, Any],
) -> str:
    """Generate a structured Markdown issue body."""
    lines: list[str] = [
        f"## Service Request: {request_type.replace('_', ' ').title()}",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| **Application Name** | {application_name} |",
        f"| **Submitted By** | {submitted_by} |",
        f"| **Timestamp** | {timestamp} |",
        "",
    ]

    if request_type == "environment_provisioning":
        lines += [
            "### Environment Details",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Business Owner | {data.get('business_owner', '—')} |",
            f"| Technical Owner | {data.get('technical_owner', '—')} |",
            f"| Cost Center | {data.get('cost_center', '—')} |",
            f"| Environment Type | {data.get('environment_type', '—')} |",
            f"| Region | {data.get('region', '—')} |",
            f"| Data Classification | {data.get('data_classification', '—')} |",
            f"| Criticality Tier | {data.get('criticality_tier', '—')} |",
            f"| Internet Exposure | {_bool_str(data.get('internet_exposure'))} |",
            f"| RTO | {data.get('rto', '—')} |",
            f"| RPO | {data.get('rpo', '—')} |",
            f"| Cloud Frontdoor Reference | {data.get('cfd_reference_id', '—')} |",
            f"| Expected Go-Live Date | {data.get('expected_go_live_date', '—')} |",
        ]
        if data.get("notes"):
            lines += ["", "### Notes", "", data["notes"]]

    elif request_type == "identity_access":
        lines += [
            "### Identity & Access Details",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Identity Type | {data.get('identity_type', '—')} |",
            f"| Scope | {data.get('scope', '—')} |",
            f"| Role Requested | {data.get('role_requested', '—')} |",
            f"| Temporary Access | {_bool_str(data.get('temporary_access'))} |",
            f"| Duration | {data.get('duration', '—')} |",
            "",
            "### Business Justification",
            "",
            data.get("business_justification", "—"),
        ]

    elif request_type == "network_connectivity":
        lines += [
            "### Network & Connectivity Details",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Connectivity Type | {data.get('connectivity_type', '—')} |",
            f"| Source | {data.get('source', '—')} |",
            f"| Destination | {data.get('destination', '—')} |",
            f"| Protocol / Port | {data.get('protocol_port', '—')} |",
            f"| Public Exposure | {_bool_str(data.get('public_exposure'))} |",
            f"| Third-Party Integration | {_bool_str(data.get('third_party_integration'))} |",
        ]

    elif request_type == "platform_services":
        lines += [
            "### Platform Service Details",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Service Type | {data.get('service_type', '—')} |",
            f"| SKU | {data.get('sku', '—')} |",
            f"| Estimated Monthly Cost (USD) | {data.get('estimated_monthly_cost_usd', '—')} |",
            f"| Backup Required | {_bool_str(data.get('backup_required'))} |",
            f"| Monitoring Required | {_bool_str(data.get('monitoring_required'))} |",
        ]

    elif request_type == "security_exception":
        lines += [
            "### Security Exception Details",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Policy / Control Violated | {data.get('policy_control_violated', '—')} |",
            f"| Expiry Date | {data.get('expiry_date', '—')} |",
            f"| Risk Acknowledged | {_bool_str(data.get('risk_acknowledged'))} |",
            "",
            "### Business Justification",
            "",
            data.get("business_justification", "—"),
            "",
            "### Compensating Controls",
            "",
            data.get("compensating_controls", "—"),
        ]

    lines += [
        "",
        "---",
        "> *This issue was automatically generated by the SDLC Service Management middleware.*",
    ]

    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────────

def create_issue(
    payload: dict[str, Any],
    github_token: str,
    github_repo: str,
) -> str:
    """
    Create a GitHub Issue from a validated webhook payload.

    Returns the HTML URL of the created issue.
    """
    request_type: str = payload["request_type"]
    application_name: str = payload["application_name"]
    submitted_by: str = payload["submitted_by"]
    timestamp: str = payload["timestamp"]
    data: dict[str, Any] = payload["data"]

    # Build title
    title_template = _TITLE_TEMPLATES[request_type]
    title = title_template.format(
        application_name=application_name,
        region=data.get("region", "unknown"),
    )

    # Build body
    body = _build_body(request_type, application_name, submitted_by, timestamp, data)

    # Resolve labels
    labels = _resolve_labels(request_type, data)

    # Create issue via GitHub API
    g = Github(github_token)
    repo = g.get_repo(github_repo)
    issue = repo.create_issue(title=title, body=body, labels=labels)

    return issue.html_url
