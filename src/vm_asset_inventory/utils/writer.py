from __future__ import annotations

from datetime import datetime
from pathlib import Path
import csv
import json

from vm_asset_inventory.models import EXPORT_FIELDS, VMAssetRecord


def export_records(records: list[VMAssetRecord], output_dir: str | Path, prefix: str = "vm_asset_inventory") -> dict:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = path / f"{prefix}-{ts}.json"
    csv_path = path / f"{prefix}-{ts}.csv"

    rows = [r.to_export_dict() for r in records]

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    headers = EXPORT_FIELDS

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "json": str(json_path),
        "csv": str(csv_path),
        "count": len(rows),
    }
