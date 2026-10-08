from __future__ import annotations

from pathlib import Path

from vm_asset_inventory.models import VMAssetRecord
from vm_asset_inventory.persistence import write_records_to_sqlserver
from vm_asset_inventory.settings import AppConfig
from vm_asset_inventory.utils.reporting import apply_record_filters, export_report_bundle
from vm_asset_inventory.utils.writer import export_records


def deliver_collection(
    config: AppConfig,
    records: list[VMAssetRecord],
    provider: str = "all",
    mode: str = "collect",
    output_dir: str | Path = "output",
) -> dict:
    mode_lower = mode.lower()
    working_records = records
    if mode_lower == "collect-report":
        working_records = apply_record_filters(records, config.report.filters)

    targets = config.output.resolve_targets()
    results: dict = {
        "raw_count": len(records),
        "count": len(working_records),
        "targets": targets,
    }

    if "database" in targets:
        db_result = write_records_to_sqlserver(working_records, config.output)
        results["database"] = {
            "batch_id": db_result.batch_id,
            "total_rows": db_result.total_rows,
            "provider_rows": db_result.provider_rows,
            "inserted_rows": db_result.inserted_rows,
            "updated_rows": db_result.updated_rows,
            "deleted_rows": db_result.deleted_rows,
            "unchanged_rows": db_result.unchanged_rows,
        }

    if "file" in targets:
        path = Path(output_dir)
        if mode_lower == "collect-report":
            file_result = export_report_bundle(working_records, output_dir=path, report_cfg=config.report)
            results["file"] = file_result
        else:
            file_result = export_records(working_records, output_dir=path)
            results["file"] = file_result

    return results
