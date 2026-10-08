# Configuration Modularization Guide

This guide defines how to manage multiple virtual platform endpoints and multiple credential sets.

## Files
- config/config.yaml: main entry file
- config/credentials.yaml: credential profiles
- config/sources.yaml: source endpoint profiles
- config/source_credentials.yaml: optional unified file for credentials + sources

## Supported modes

### Mode A: Split files (existing)
- credentials and sources are stored in separate files.
- `modules.credentials_file` and `modules.sources_file` are both used.

### Mode B: Unified file (new)
- credentials and sources are stored in one file.
- set `modules.source_credentials_file` in `config/config.yaml`.
- recommended for easier editing and fewer cross-file references.

Example:

modules:
	source_credentials_file: config/source_credentials.yaml
	proxy_file: ../../shared_proxy/proxy.yaml

### Mode C: Sources-only inline auth
- credentials registry can be omitted.
- define `username` with `password` or `password_env` directly in each source item.
- this mode works in unified file or legacy single sources file setup.

## Credential profile format
Per provider, define multiple credential records:

- nutanix[].id
- nutanix[].username
- nutanix[].password or nutanix[].password_env
- vmware[].id
- vmware[].username
- vmware[].password or vmware[].password_env

Use password_env when possible.

## Source profile format
Each source references credential_id:

- nutanix[].name
- nutanix[].base_url
- nutanix[].credential_id
- vmware[].name
- vmware[].host
- vmware[].credential_id

Or define inline auth fields:

- nutanix[].username
- nutanix[].password or nutanix[].password_env
- vmware[].username
- vmware[].password or vmware[].password_env

## Add a new platform endpoint
1. Choose mode A/B/C.
2. If using credential registry (A/B), add credential profile first.
3. Add source profile and bind `credential_id` (A/B) or inline auth (C).
4. Set env var if password_env is used.
5. Run collector.

## Validation rules
- credential_id must exist in matching provider credentials list.
- duplicate credential id in same provider is not allowed.
- password resolution must not be empty.
- inline password_env must resolve to non-empty value when used.

## Backward compatibility
Inline legacy mode in config.yaml with username/password per source is still supported, but modular mode is recommended.

## Migration recommendation (split -> unified)
1. Create `config/source_credentials.yaml` by combining `credentials.yaml` and `sources.yaml`.
2. Set `modules.source_credentials_file` in `config/config.yaml`.
3. Keep original two files for one transition cycle.
4. Verify output equivalence, then retire split files.
