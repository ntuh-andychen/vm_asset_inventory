# API Compliance Guide (Nutanix / VMware)

## Purpose
This document defines API development rules for this project so collector scripts stay aligned with official platform guidance.

## Official references
- Nutanix Prism Central v3 API reference:
  - https://www.nutanix.dev/api_references/prism-central-v3/
- VMware vSphere Automation API reference:
  - https://developer.broadcom.com/xapis/vsphere-automation-api/latest/
- VMware vSphere Web Services API reference (pyVmomi-based):
  - https://developer.broadcom.com/xapis/vsphere-web-services-api/latest/

## Nutanix API rules (RESTful)
- Use HTTPS only.
- Keep endpoint paths under `/api/nutanix/v3`.
- Use standard HTTP semantics:
  - `POST /vms/list` for paginated inventory query.
  - Handle HTTP status codes explicitly via `raise_for_status()`.
- Request/response format:
  - `Content-Type: application/json`
  - `Accept: application/json`
- Pagination:
  - Use `offset` + `length` and continue until `total_matches` reached.
- Reliability:
  - Retry only transient failures (timeout/connection).
  - Keep exponential backoff.
- Security:
  - `verify_ssl: true` in production.
  - Use `ca_bundle` for internal CA chain when required.

## VMware API rules
- Current implementation is pyVmomi (vSphere Web Services API).
- Use HTTPS/TLS and verified SSL by default in production.
- Use authenticated session via `SmartConnect` and always disconnect (`Disconnect`).
- Scope calls to minimum required inventory objects (VirtualMachine only in this phase).
- Keep behavior aligned with VMware object model contracts from official docs.

## Common API coding standards
- Never hardcode proxy URL or credentials in source code.
- Read config externally from YAML + environment variables.
- Keep request timeout explicit.
- Surface endpoint-level errors in connection test mode.
- Keep collector logic read-only (no mutation/write API calls) for inventory phase.

## Certificate-chain policy
- CA chain file path is standardized at:
  - `certs/internal-ca-chain.pem`
- Endpoints should set:
  - `verify_ssl: true`
  - `ca_bundle: certs/internal-ca-chain.pem`
- Replace placeholder certificate content with actual internal CA PEM chain before production run.
