# Reporting and DB Preparation Spec

## Goal
Collect VM inventory from Nutanix and VMware based on configurable conditions, then output:
- detailed dataset for ETL/load
- aggregated summary report for capacity/operations review

## Runtime mode
Use report mode:
- `./run.ps1 -Provider all -Mode collect-report -ConfigPath config/config.yaml`

This mode performs:
1. source collection
2. condition filtering
3. database write when enabled in YAML
4. detailed report export when file output or debug mode is enabled
5. summary report export when file output or debug mode is enabled

## Output control in YAML
Top-level `output` section controls delivery behavior.

Key fields:
- `output.mode`: `auto`, `database`, `file`, `both`
- `output.debug_files`: force file output for debugging
- `output.sqlserver.enabled`: enable SQL Server write path
- `output.sqlserver.server`: remote SQL Server host name
- `output.sqlserver.local_server`: local test SQL Server host name
- `output.sqlserver.connection_mode`: `auto`, `remote`, `local`
- `output.sqlserver.database`: target database name, default `ExampleInventory`
- `output.sqlserver.authentication`: `integrated` or `sql`
- `output.sqlserver.table_map`: provider to table mapping

Delivery rule:
- `auto`: use remote server when provided; otherwise fall back to local server; if DB is disabled then write files
- `database`: require database enabled
- `file`: file output only
- `both`: database plus files (when database enabled)

Connection rule:
- If `connection_mode` is `remote`, use `server`
- If `connection_mode` is `local`, use `local_server`
- If `connection_mode` is `auto`, prefer `server`, otherwise fallback to `local_server`

## Condition configuration
Configure in `config/source_credentials.yaml` under top-level `report`.

Fields:
- `report.output_prefix`: output file prefix
- `report.summary_group_by`: aggregation dimensions
- `report.filters.providers`: limit source providers (`nutanix`, `vmware`)
- `report.filters.platforms`: limit endpoint platform names
- `report.filters.powerstates`: limit power states (for example `on`)
- `report.filters.vmname_contains`: substring match on VM name
- `report.filters.cluster_contains`: substring match on cluster name
- `report.filters.min_ram_mib`: minimum RAM threshold
- `report.filters.min_disk_gb`: minimum Disk threshold
- `report.filters.require_ip`: only keep rows with non-empty IP

## Output artifacts
Generated in output directory:
- `<prefix>-detail-<timestamp>.json`
- `<prefix>-detail-<timestamp>.csv`
- `<prefix>-summary-<timestamp>.json`
- `<prefix>-summary-<timestamp>.csv`

Summary metrics per group:
- `count`
- `total_ram_mib`
- `total_disk_gb`
- `total_vcpu`

## Database preparation mapping
Use detailed report as stage input (`stg_vm_asset_inventory_raw`).

Recommended DB load columns:
- all canonical output columns from collector
- plus batch metadata:
  - `BatchId`
  - `CollectedAt`
  - `SourceProvider`
  - `SourcePlatform`

Recommended flow:
1. load detail CSV/JSON to staging
2. deduplicate by (`source_provider`, `source_platform`, `vm_uuid`, `collected_at`)
3. apply quality checks (required fields, ip/mac formatting)
4. merge into target source tables (`src_nutanix.VirtualMachine`, `src_vmware.VirtualMachine`)

## Testing checklist
1. `test-connection` all endpoints pass
2. `collect-report` completes with non-zero detail count
3. summary groups match expected dimensions
4. sample rows verify required fields (`sock`, `vCore`, `vTotalCore`, `RAM`, `Disk`, `ip`, `mac`)
