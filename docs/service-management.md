# SDLC Cloud Service Management – Specification Reference

## Purpose

This model provides a **lightweight, automation-first execution layer** for managing **approved cloud workloads** during SDLC phases (Sandbox, Dev, UAT).

It **does not replace or bypass** Maybank Cloud Frontdoor (CFD). Cloud Frontdoor remains the **system of record** for cloud suitability, onboarding, and risk decisions.

---

## Relationship to Cloud Frontdoor

| Area | Cloud Frontdoor (CFD) | SDLC Service Management |
|------|----------------------|-------------------------|
| Primary role | Decide **whether** a workload may enter cloud | Govern **how** approved workloads are executed |
| Phase | Pre-planning / onboarding | SDLC execution (Sandbox, Dev, UAT) |
| Assessments | Cloud fitment, security, compliance | None |
| Decision authority | Experimentation vs Prod path | No decision authority |
| Governance style | Questionnaire-based, shift-left | Policy-as-code, CI/CD enforcement |
| Output | Cloud suitability decision | Executed infrastructure and access |

> **Explicit Guardrail:** This model is only applicable **after** a workload has received a positive Cloud Frontdoor outcome.

---

## Scope

### In Scope

- SDLC cloud execution requests (Sandbox, Dev, UAT)
- Non-human IAM at workload level
- Network connectivity enablement
- Standard platform services provisioning
- Time-bound security exceptions (execution only)

### Explicitly Out of Scope

- Cloud suitability decisions
- Experimentation vs Production pathway
- Production environment provisioning
- User IAM and break-glass access
- Incident and change management
- Regulatory risk acceptance decisions

---

## Operational Flow

```
1. User submits simple form
2. Form emits JSON webhook → middleware/app.py
3. Middleware validates schema, resolves labels, creates GitHub Issue
4. Cloud Ops triages backlog
5. IaC PR raised
6. Pipelines enforce governance (.github/workflows/validate-request.yml)
7. Deployment executed
8. Full audit trail via Issue + PR history
```

---

## Governance & Control Model

| Control Area | Enforcement Location |
|--------------|---------------------|
| Cloud suitability | Cloud Frontdoor |
| Internet exposure | PR review + policy scan |
| Elevated IAM | CODEOWNERS security review |
| Non-standard SKU | Cost validation pipeline |
| Missing tags | IaC validation failure |

---

## Label Taxonomy

| Category | Labels |
|----------|--------|
| Request Type | `environment`, `iam`, `network`, `platform`, `security-exception` |
| Environment | `sandbox`, `dev`, `uat` |
| Risk Indicators | `public`, `confidential`, `restricted` |
| Cost | `high-cost` |
| Lifecycle | `decommission` |

Labels are applied automatically by the middleware and the `validate-request` workflow.
