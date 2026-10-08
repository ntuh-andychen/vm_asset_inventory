from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import csv
import json

from vm_asset_inventory.models import EXPORT_FIELDS, VMAssetRecord
from vm_asset_inventory.settings import ReportConfig, ReportFilterConfig


def apply_record_filters(records: list[VMAssetRecord], filters: ReportFilterConfig) -> list[VMAssetRecord]:
    providers = {x.lower() for x in filters.providers}
    platforms = {x for x in filters.platforms}
    powerstates = {x.lower() for x in filters.powerstates}

    vmname_keyword = filters.vmname_contains.strip().lower()
    cluster_keyword = filters.cluster_contains.strip().lower()

    out: list[VMAssetRecord] = []
    for item in records:
        if providers and item.source_provider.lower() not in providers:
            continue
        if platforms and item.source_platform not in platforms:
            continue
        if powerstates and item.powerstate.lower() not in powerstates:
            continue
        if vmname_keyword and vmname_keyword not in item.vmname.lower():
            continue
        if cluster_keyword and cluster_keyword not in item.cluster.lower():
            continue
        if item.RAM < filters.min_ram_mib:
            continue
        if item.Disk < filters.min_disk_gb:
            continue
        if filters.require_ip and not item.ip.strip():
            continue
        out.append(item)

    return out


def _build_summary_rows(records: list[VMAssetRecord], report_cfg: ReportConfig) -> list[dict]:
    group_keys = report_cfg.summary_group_by

    buckets: dict[tuple, dict] = defaultdict(
        lambda: {
            "count": 0,
            "total_ram_gb": 0.0,
            "total_vcpu": 0,
        }
    )

    for row in records:
        row_data = row.to_dict()
        key = tuple(row_data.get(k, "") for k in group_keys)
        bucket = buckets[key]
        bucket["count"] += 1
        bucket["total_ram_gb"] += float(row.RAM) / 1024.0
        bucket["total_vcpu"] += int(row.vTotalCore)

    rows: list[dict] = []
    for key, value in buckets.items():
        line: dict = {}
        for idx, key_name in enumerate(group_keys):
            line[key_name] = key[idx]
        line["count"] = value["count"]
        line["total_ram_gb"] = round(value["total_ram_gb"], 2)
        line["total_vcpu"] = value["total_vcpu"]
        rows.append(line)

    rows.sort(key=lambda x: tuple(str(x.get(k, "")) for k in group_keys))
    return rows


def export_report_bundle(
    records: list[VMAssetRecord],
    output_dir: str | Path,
    report_cfg: ReportConfig,
) -> dict:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    prefix = report_cfg.output_prefix

    detail_json = path / f"{prefix}-detail-{ts}.json"
    detail_csv = path / f"{prefix}-detail-{ts}.csv"
    summary_json = path / f"{prefix}-summary-{ts}.json"
    summary_csv = path / f"{prefix}-summary-{ts}.csv"

    detail_rows = [x.to_export_dict() for x in records]
    summary_rows = _build_summary_rows(records, report_cfg)

    with detail_json.open("w", encoding="utf-8") as f:
        json.dump(detail_rows, f, ensure_ascii=False, indent=2)

    detail_headers = EXPORT_FIELDS
    with detail_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=detail_headers)
        writer.writeheader()
        writer.writerows(detail_rows)

    with summary_json.open("w", encoding="utf-8") as f:
        json.dump(summary_rows, f, ensure_ascii=False, indent=2)

    summary_headers = report_cfg.summary_group_by + ["count", "total_ram_gb", "total_vcpu"]
    with summary_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_headers)
        writer.writeheader()
        writer.writerows(summary_rows)

    return {
        "detail_json": str(detail_json),
        "detail_csv": str(detail_csv),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "detail_count": len(detail_rows),
        "summary_count": len(summary_rows),
        "applied_filters": asdict(report_cfg.filters),
        "summary_group_by": report_cfg.summary_group_by,
    }
