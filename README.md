# ISDRepo

# SDLC Cloud Service Management

A **lightweight, automation-first** execution layer for managing approved cloud workloads during SDLC phases (Sandbox, Dev, UAT), implemented as a GitHub-Driven Execution Model.

> **Guardrail:** This model is only applicable **after** a workload has received a positive [Cloud Frontdoor](docs/service-management.md#relationship-to-cloud-frontdoor) outcome.

---

## What This Repository Provides

| Component | Description |
|-----------|-------------|
| `middleware/` | Python/Flask webhook receiver that converts intake form submissions into GitHub Issues |
| `.github/ISSUE_TEMPLATE/` | Five structured issue templates (one per service request type) |
| `.github/labels.yml` | Label taxonomy for automated issue classification |
| `.github/workflows/validate-request.yml` | GitHub Actions workflow that validates issues and applies labels |
| `.github/workflows/test.yml` | CI workflow that runs middleware tests |
| `.github/scripts/validate_issue.py` | Validation logic used by the Actions workflow |

---

## Service Request Types

| Prefix | Type | Purpose |
|--------|------|---------|
| `ENV` | Environment Provisioning | SDLC environment execution (Sandbox / Dev / UAT only) |
| `IAM` | Identity & Access (Non-Human) | Managed Identity / Service Principal |
| `NET` | Network & Connectivity | Private Endpoint / Firewall Rule / API Exposure |
| `PLAT` | Platform Services | Database / Storage / Queue / Cache / AI-ML |
| `SEC-EX` | Security Exception | Time-bound policy deviation (expiry date mandatory) |

---

## Webhook Integration

The middleware exposes a single endpoint that accepts standardised JSON webhooks from intake forms:

```bash
POST /webhook
Content-Type: application/json

{
  "request_type": "environment_provisioning",
  "application_name": "Payments API",
  "submitted_by": "user@company.com",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": { ... }
}
```

On success, returns:
```json
{ "issue_url": "https://github.com/org/cloud-ops-backlog/issues/42" }
```

### Running the Middleware

```bash
cd middleware
pip install -r requirements.txt
GITHUB_TOKEN=<token> GITHUB_REPO=org/cloud-ops-backlog flask --app app run
```

### Running Tests

```bash
pip install -r middleware/requirements-dev.txt
pytest -v
```

---

## Design Principles

1. **Cloud Frontdoor remains authoritative** for onboarding decisions.
2. **Execution, not assessment** – no suitability or risk questionnaires.
3. **No approval workflows** in the intake layer.
4. **Automation first** – governance enforced via pipelines, not humans.
5. **Single operational backlog** (GitHub Issues).
6. **Audit by design** – full traceability via Issues, PRs, and pipeline logs.

See [docs/service-management.md](docs/service-management.md) for the full specification.
