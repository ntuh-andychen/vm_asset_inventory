from __future__ import annotations

import argparse
from pathlib import Path

from vm_asset_inventory.delivery import deliver_collection
from vm_asset_inventory.persistence.sqlserver import initialize_sqlserver_schema
from vm_asset_inventory.settings import load_config
from vm_asset_inventory.service import collect_assets, test_connections


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VM asset inventory collector")
    parser.add_argument("--config", default="config/config.yaml", help="Path to YAML config")
    parser.add_argument(
        "--provider",
        default="all",
        help="Data source provider (all, nutanix, vmware; extensible)",
    )
    parser.add_argument(
        "--mode",
        default="collect",
        choices=["collect", "collect-report", "test-connection"],
        help="Run data collection, report generation, or connection tests",
    )
    parser.add_argument("--output-dir", default="", help="Override output directory")
    parser.add_argument(
        "--init-database",
        action="store_true",
        help="Create or update the SQL Server schema before any data collection",
    )
    parser.add_argument("--ddl-path", default=None, help="Override schema DDL path")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.init_database:
        ddl_path = Path(args.ddl_path) if args.ddl_path else None
        result = initialize_sqlserver_schema(cfg.output, ddl_path=ddl_path)
        print(f"Database schema initialized on {result.server} using {result.script_path}")
        return 0

    if args.mode == "test-connection":
        results = test_connections(cfg, provider=args.provider)
        ok_count = sum(1 for x in results if bool(x.get("success")))
        fail_count = len(results) - ok_count

        for item in results:
            status = "OK" if item["success"] else "FAIL"
            print(f"[{status}] {item['provider']}:{item['endpoint']} - {item['message']}")

        print(f"Connection test summary: total={len(results)} ok={ok_count} fail={fail_count}")
        return 0 if fail_count == 0 else 2

    records = collect_assets(cfg, provider=args.provider)
    output_dir = args.output_dir or cfg.general.output_dir
    result = deliver_collection(cfg, records, provider=args.provider, mode=args.mode, output_dir=Path(output_dir))

    if args.mode == "collect-report":
        print(f"Collected records (raw): {result['raw_count']}")
        print(f"Collected records (filtered): {result['count']}")
        if "database" in result:
            print(f"Database batch id: {result['database']['batch_id']}")
            print(f"Database rows: {result['database']['total_rows']}")
            print(f"Database inserted rows: {result['database']['inserted_rows']}")
            print(f"Database updated rows: {result['database']['updated_rows']}")
            print(f"Database deleted rows: {result['database']['deleted_rows']}")
            print(f"Database unchanged rows: {result['database']['unchanged_rows']}")
        if "file" in result:
            print(f"Summary groups: {result['file']['summary_count']}")
            print(f"Detail JSON: {result['file']['detail_json']}")
            print(f"Detail CSV: {result['file']['detail_csv']}")
            print(f"Summary JSON: {result['file']['summary_json']}")
            print(f"Summary CSV: {result['file']['summary_csv']}")
            print(f"Group by: {', '.join(result['file']['summary_group_by'])}")
        return 0

    print(f"Collected records: {result['count']}")
    if "database" in result:
        print(f"Database batch id: {result['database']['batch_id']}")
        print(f"Database rows: {result['database']['total_rows']}")
        print(f"Database inserted rows: {result['database']['inserted_rows']}")
        print(f"Database updated rows: {result['database']['updated_rows']}")
        print(f"Database deleted rows: {result['database']['deleted_rows']}")
        print(f"Database unchanged rows: {result['database']['unchanged_rows']}")
    if "file" in result:
        print(f"JSON: {result['file']['json']}")
        print(f"CSV: {result['file']['csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
