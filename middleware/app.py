"""
SDLC Service Management – Webhook Receiver Middleware

Receives standardised JSON webhooks from intake forms, validates the payload,
generates a structured GitHub Issue, and returns the issue URL to the caller.

Usage:
    GITHUB_TOKEN=<token> GITHUB_REPO=<owner/repo> flask run
"""
from __future__ import annotations

import os
from flask import Flask, Response, jsonify, request

from .issue_creator import create_issue
from .schema import SchemaValidationError, validate_payload

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook() -> tuple[Response, int]:
    """
    Accept a service request webhook and create a GitHub Issue.

    Expected Content-Type: application/json
    Returns: {"issue_url": "<url>"} on success or {"error": "<message>"} on failure.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid JSON payload"}), 400

    try:
        validate_payload(payload)
    except SchemaValidationError as exc:
        return jsonify({"error": str(exc)}), 422

    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_repo = os.environ.get("GITHUB_REPO", "cloud-ops-backlog")

    if not github_token:
        return jsonify({"error": "Server configuration error: GITHUB_TOKEN not set"}), 500

    issue_url = create_issue(payload, github_token, github_repo)
    return jsonify({"issue_url": issue_url}), 201


@app.route("/healthz", methods=["GET"])
def health() -> tuple[Response, int]:
    """Liveness probe."""
    return jsonify({"status": "ok"}), 200
