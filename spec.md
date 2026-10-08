# VM Asset Inventory Spec (Phase 1)

## Governance basis
This project follows:
- C:/Projects/Python/specification/constitution.md
- C:/Projects/Python/specification/naming-convention.md

## Scope
- Build a reusable modular collector for VM asset inventory.
- Source systems in this phase: Nutanix and VMware only.
- Deliverable: inventory outputs for table/query design.
- Excluded in this phase: creating database tables.

## Architecture
- Provider modules are fully separated:
  - vm_asset_inventory.providers.nutanix
  - vm_asset_inventory.providers.vmware
- Shared model:
  - vm_asset_inventory.models.VMAssetRecord
- Shared service orchestration:
  - vm_asset_inventory.service.collect_assets
- CLI:
  - vm_asset_inventory.cli
- Modular configuration:
  - config/config.yaml (main)
  - config/credentials.yaml (credential registry)
  - config/sources.yaml (source registry)
  - sources reference credentials by credential_id
  - optional unified mode: config/source_credentials.yaml (credentials + sources in one file)

## Data requirements implemented
The collector outputs these required fields:
- sock
- vCore
- vTotalCore
- RAM
- Disk
- vlanname (delimiter `:`)
- vlanid (delimiter `:`)
- ip (delimiter `:`)
- mac (delimiter `:`)
- disk_spec
- describ

## Output format
- JSON and CSV in output directory.
- Timestamped filenames.
- Multi-value fields normalized with `:`.
- Report mode also outputs aggregated summary (grouped metrics) for DB preparation.

## Multi-platform scalability
- Support multiple Nutanix and VMware endpoints simultaneously.
- Support multiple account sets per provider using credential profiles.
- New platform endpoint onboarding requires YAML changes only (no code changes for same provider type).
- Unified config mode reduces cross-file editing overhead while keeping profile reuse.

## Next phase
- Design source tables under ExampleInventory:
  - src_nutanix.VirtualMachine
  - src_vmware.VirtualMachine
- Add staging/integration strategy after validating real output samples.
- Use `collect-report` mode with configured filters to produce ETL-ready detail dataset and summary metrics.
