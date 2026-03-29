"""
GitHub Actions validation script for SDLC service request issues.

Reads issue metadata from environment variables, validates required fields,
applies labels, and fails the pipeline on violations.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

from github import Github

# ── Constants ──────────────────────────────────────────────────────────────────

HIGH_COST_THRESHOLD_USD = 1000

ISSUE_TYPE_PREFIXES: dict[str, str] = {
    "ENV": "environment",
    "IAM": "iam",
    "NET": "network",
    "PLAT": "platform",
    "SEC-EX": "security-exception",
}

ENVIRONMENT_KEYWORDS: dict[str, str] = {
    "sandbox": "sandbox",
    "dev": "dev",
    "uat": "uat",
}

DATA_CLASSIFICATION_LABELS: dict[str, str] = {
    "public": "public",
    "confidential": "confidential",
    "restricted": "restricted",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_field(body: str, field_name: str) -> str | None:
    """Extract a form field value from a GitHub issue body (markdown form)."""
    pattern = rf"###\s+{re.escape(field_name)}\s*\n+(.+?)(?:\n###|\Z)"
    match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
    if match:
        value = match.group(1).strip()
        return value if value and value.lower() != "_no response_" else None
    return None


def detect_request_type(title: str) -> str | None:
    """Return the canonical label name for the request type based on title prefix."""
    for prefix, label in ISSUE_TYPE_PREFIXES.items():
        if title.upper().startswith(f"{prefix} |") or title.upper().startswith(f"{prefix}|"):
            return label
    return None


def collect_labels(
    request_type_label: str,
    body: str,
    title: str,
) -> list[str]:
    """Determine which labels should be applied to the issue."""
    labels: list[str] = [request_type_label]

    body_lower = body.lower()

    # Environment label (ENV requests and any that mention env type)
    for keyword, label in ENVIRONMENT_KEYWORDS.items():
        if keyword in body_lower or keyword in title.lower():
            labels.append(label)
            break

    # Data classification / risk labels
    for keyword, label in DATA_CLASSIFICATION_LABELS.items():
        if keyword in body_lower:
            labels.append(label)
            break

    # Public exposure
    exposure_value = _get_field(body, "Internet Exposure") or _get_field(body, "Public Exposure")
    if exposure_value and exposure_value.lower() == "yes":
        if "public" not in labels:
            labels.append("public")

    # High-cost detection
    cost_str = _get_field(body, "Estimated Monthly Cost (USD)") or _get_field(body, "Estimated Monthly Cost")
    if cost_str:
        digits = re.sub(r"[^\d.]", "", cost_str)
        try:
            if float(digits) >= HIGH_COST_THRESHOLD_USD:
                labels.append("high-cost")
        except ValueError:
            pass

    return list(dict.fromkeys(labels))  # deduplicate, preserve order


def validate_expiry_date(body: str) -> list[str]:
    """Return a list of validation errors for security exception expiry date."""
    errors: list[str] = []
    expiry = _get_field(body, "Expiry Date (Mandatory)") or _get_field(body, "Expiry Date")
    if not expiry:
        errors.append("Security Exception requests MUST include an Expiry Date.")
    else:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", expiry.strip()):
            errors.append(f"Expiry Date '{expiry}' is not in YYYY-MM-DD format.")
    return errors


def validate_environment_type(body: str) -> list[str]:
    """Ensure environment requests target non-production environments only."""
    errors: list[str] = []
    env_type = _get_field(body, "Environment Type")
    if not env_type:
        errors.append("Environment Type is required (Sandbox / Dev / UAT).")
    elif env_type.strip().lower() not in {"sandbox", "dev", "uat"}:
        errors.append(
            f"Environment Type '{env_type}' is not allowed. "
            "Only Sandbox, Dev, or UAT are permitted (non-production only)."
        )
    return errors


def validate_issue(title: str, body: str, request_type_label: str) -> list[str]:
    """Run all validations. Returns list of error messages (empty means pass)."""
    errors: list[str] = []

    # Application name is required for all request types
    app_name = _get_field(body, "Application Name")
    if not app_name:
        errors.append("Application Name is required for all service requests.")

    # Type-specific validation
    if request_type_label == "environment":
        errors.extend(validate_environment_type(body))

    if request_type_label == "security-exception":
        errors.extend(validate_expiry_date(body))

    # Tagging: internet/public exposure requires documentation
    exposure = _get_field(body, "Internet Exposure") or _get_field(body, "Public Exposure")
    if exposure and exposure.lower() == "yes":
        justification = (
            _get_field(body, "Business Justification")
            or _get_field(body, "Notes")
        )
        if not justification:
            errors.append(
                "Public/Internet exposure requires a Business Justification or Notes entry."
            )

    return errors


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    token = os.environ["GITHUB_TOKEN"]
    repo_name = os.environ["REPO_FULL_NAME"]
    issue_number = int(os.environ["ISSUE_NUMBER"])
    title = os.environ.get("ISSUE_TITLE", "")
    body = os.environ.get("ISSUE_BODY", "") or ""

    g = Github(token)
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(issue_number)

    # Detect request type from title
    request_type_label = detect_request_type(title)
    if not request_type_label:
        print(
            f"::error::Issue title '{title}' does not match any known request type prefix "
            "(ENV | IAM | NET | PLAT | SEC-EX). No validation performed."
        )
        sys.exit(1)

    print(f"Detected request type: {request_type_label}")

    # Validate
    errors = validate_issue(title, body, request_type_label)

    # Compute and apply labels
    labels_to_apply = collect_labels(request_type_label, body, title)
    print(f"Applying labels: {labels_to_apply}")

    existing_label_names = [lbl.name for lbl in issue.labels]
    for label_name in labels_to_apply:
        if label_name not in existing_label_names:
            try:
                issue.add_to_labels(label_name)
            except Exception as exc:  # noqa: BLE001
                print(f"::warning::Could not apply label '{label_name}': {exc}")

    if errors:
        for err in errors:
            print(f"::error::{err}")
        sys.exit(1)

    print("Validation passed.")


if __name__ == "__main__":
    main()
