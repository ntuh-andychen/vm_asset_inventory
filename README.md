# vm_asset_inventory

This project is a modular VM asset inventory collector under `C:/Projects/Python`.

Scope for phase 1:
- Collect only Nutanix and VMware source data.
- Keep providers separated as independent modules.
- Export collected inventory first, then design database tables later.

Design constraints:
- Follow specification in `C:/Projects/Python/specification`.
- Modular package structure with provider-level importability.
- Multi-value fields use `:` as delimiter.

## Project structure
- `src/vm_asset_inventory/providers/nutanix`: Nutanix module
- `src/vm_asset_inventory/providers/vmware`: VMware module
- `src/vm_asset_inventory/models.py`: shared inventory record model
- `src/vm_asset_inventory/settings.py`: config schema and loader
- `src/vm_asset_inventory/cli.py`: command-line entry
- `spec.md`: phase scope and governance alignment
- `config/config.template.yaml`: config template
- `config/credentials.template.yaml`: provider credential template
- `config/sources.template.yaml`: provider source endpoint template
- `config/source_credentials.template.yaml`: unified source+credential template
- `config/proxy.template.yaml`: modular proxy profiles and feature bindings
- `docs/python-uv-offline-proxy.md`: proxy + offline Python/uv workflow
- `docs/api-compliance.md`: Nutanix/VMware API development compliance guide
- `docs/reporting-db-prep.md`: condition-based reporting and DB preparation spec
- `scripts/prepare-offline-python-uv.ps1`: build offline bundle on connected machine
- `scripts/install-offline-python-uv.ps1`: install from offline bundle
- `output/`: exported inventory files
- `docs/source-field-inventory.md`: source field inventory and DB planning notes

## Required output fields
- sock
- vCore
- vTotalCore
- RAM
- Disk
- vlanname (multi-value with `:`)
- vlanid (multi-value with `:`)
- ip (multi-value with `:`)
- mac (multi-value with `:`)
- disk spec
- describ

## Quick start
1. Copy config template
2. Fill credentials
3. Run collector

Example:
- `uv run vm-asset-inventory --config config/config.yaml --provider all`
- `./run.ps1 -Provider all -ConfigPath config/config.yaml`
- `./run.ps1 -Provider all -Mode test-connection -ConfigPath config/config.yaml`
- `./run.ps1 -Provider all -Mode collect-report -ConfigPath config/config.yaml`

Offline-first behavior of `run.ps1`:
- use `uv` from PATH if available
- else use bundled `output/offline_bundle*/uv-bin/uv.exe`
- else fallback to `.venv/Scripts/python.exe`

## SSL and certificate bundle
- For encrypted and verified TLS, set `verify_ssl: true` on each endpoint.
- If your internal CA is not in OS trust store, provide `ca_bundle` (PEM file path).
- `ca_bundle` can be absolute path or relative to the source config file.

Example endpoint TLS fields:
- Nutanix: `verify_ssl: true`, `ca_bundle: certs/EXAMPLE-ca-chain.pem`
- VMware: `verify_ssl: true`, `ca_bundle: certs/EXAMPLE-ca-chain.pem`

Connection test mode:
- `--mode test-connection` validates TLS/auth/connectivity without inventory export.

Condition-based report mode:
- `--mode collect-report` runs collection, applies configured filters, and exports detail + summary reports.

Output delivery control:
- `output.mode` in YAML controls `auto`, `database`, `file`, or `both`
- `output.sqlserver.enabled` turns database write on/off
- `output.debug_files` keeps file output for troubleshooting
- default behavior stays file-safe until the database path is enabled

## Multi-platform credential model
- `config/config.yaml`: main config (loads module files)
- `config/credentials.yaml`: all account/password profiles
- `config/sources.yaml`: all Nutanix/VMware endpoints
- Each source uses `credential_id` to reference credentials

Unified option:
- `config/source_credentials.yaml`: keep `credentials` + `sources` in one file
- set `modules.source_credentials_file` in `config/config.yaml`
- inline `password_env` per source is supported when needed

Recommended secret mode:
- keep `username` in `credentials.yaml`
- keep password in env var via `password_env`

Example extension flow:
1. add one credential profile in `credentials.yaml`
2. add one source endpoint in `sources.yaml`
3. set related environment variable (if using `password_env`)
4. run with `--provider nutanix` or `--provider vmware` or `--provider all`

Initial simulated setup in this repository:
- Nutanix credentials: 3 sets
- Nutanix sources: 3 endpoints
- VMware credentials: 3 sets
- VMware sources: 3 endpoints

## Modular proxy model
- Cross-project shared proxy settings are defined in `../shared_proxy/proxy.yaml`.
- `feature_bindings` controls which feature uses which proxy profile.
- Only features that need external connectivity should use proxy bindings.
- Example feature names:
	- `offline_download`
	- `dependency_download`
	- `version_check`
	- `nutanix_api`
	- `vmware_api`
- Shared module files:
	- `../shared_proxy/scripts/ProxyConfig.psm1`
	- `../shared_proxy/python/proxy_config.py`

## Notes
- This phase does not create database tables.
- Output is intended for table design in next phase.

## Independent module usage
- Nutanix only import path:
	- `from vm_asset_inventory.providers.nutanix import collect_nutanix`
- VMware only import path:
	- `from vm_asset_inventory.providers.vmware import collect_vmware`

部署此 GitHub 版本前，請先閱讀 [設定與依賴說明](GITHUB_SETUP.md)。
