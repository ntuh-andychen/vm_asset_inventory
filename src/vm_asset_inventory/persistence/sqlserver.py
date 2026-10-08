from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import os
from typing import Iterable

import pyodbc

from vm_asset_inventory.models import EXPORT_FIELDS, VMAssetRecord
from vm_asset_inventory.settings import ConfigError, OutputConfig, SqlServerTargetConfig


@dataclass
class SqlServerWriteResult:
    batch_id: str
    total_rows: int
    provider_rows: dict[str, int]
    inserted_rows: int
    updated_rows: int
    deleted_rows: int
    unchanged_rows: int
    script_path: str


@dataclass
class SqlServerSchemaResult:
    script_path: str
    server: str


COMPARE_FIELDS = [field for field in EXPORT_FIELDS if field not in {"vm_uuid", "collected_at"}]


def write_records_to_sqlserver(records: list[VMAssetRecord], output_config: OutputConfig) -> SqlServerWriteResult:
    sql_cfg = output_config.sqlserver
    if not sql_cfg.enabled:
        return SqlServerWriteResult(
            batch_id="",
            total_rows=0,
            provider_rows={},
            inserted_rows=0,
            updated_rows=0,
            deleted_rows=0,
            unchanged_rows=0,
            script_path="",
        )

    resolved_server = sql_cfg.resolve_server()
    if not resolved_server:
        raise ConfigError(
            "SQL Server connection is enabled but no remote_server or local_server is configured in output.sqlserver"
        )

    grouped: dict[str, list[dict]] = {}
    for record in records:
        provider = record.source_provider.lower()
        grouped.setdefault(provider, []).append(record.to_export_dict())

    batch_id = _create_batch_id(sorted(grouped.keys()))
    _create_batch_log(
        sql_cfg,
        resolved_server,
        batch_id=batch_id,
        batch_scope=",".join(sorted(grouped.keys())) or "none",
        raw_record_count=len(records),
        processed_record_count=sum(len(rows) for rows in grouped.values()),
    )

    provider_rows: dict[str, int] = {}
    total_rows = 0
    inserted_rows = 0
    updated_rows = 0
    deleted_rows = 0
    unchanged_rows = 0
    batch_items: list[dict[str, object]] = []

    try:
        for provider, rows in grouped.items():
            table_name = _resolve_table_name(sql_cfg, provider)
            if not table_name:
                raise ConfigError(f"No table mapping defined for provider: {provider}")

            current_rows = _dedupe_rows_by_vm_uuid(rows)
            if not current_rows:
                provider_rows[provider] = 0
                continue

            existing_rows = _load_existing_rows(sql_cfg, resolved_server, table_name, list(current_rows.keys()))

            provider_inserts: list[dict] = []
            provider_updates: list[dict] = []
            provider_deletes: list[dict] = []
            provider_unchanged = 0

            for vm_uuid, row in current_rows.items():
                existing_row = existing_rows.get(vm_uuid)
                if existing_row is None:
                    provider_inserts.append(row)
                    batch_items.append(_build_batch_item(batch_id, provider, table_name, row, "inserted", ""))
                    continue

                changed_fields = _get_changed_fields(existing_row, row)
                if changed_fields:
                    provider_updates.append(row)
                    batch_items.append(
                        _build_batch_item(batch_id, provider, table_name, row, "updated", ",".join(changed_fields))
                    )
                else:
                    provider_unchanged += 1
                    batch_items.append(_build_batch_item(batch_id, provider, table_name, row, "unchanged", ""))

            missing_rows = _load_missing_active_rows(sql_cfg, resolved_server, table_name, set(current_rows.keys()))
            for missing_row in missing_rows:
                provider_deletes.append(missing_row)
                batch_items.append(
                    _build_batch_item(
                        batch_id,
                        provider,
                        table_name,
                        missing_row,
                        "deleted",
                        "missing_from_source",
                    )
                )

            _apply_changes(
                sql_cfg,
                resolved_server,
                table_name,
                batch_id,
                provider_inserts,
                provider_updates,
                provider_deletes,
            )
            _sync_lifecycle_records(
                sql_cfg, resolved_server, table_name, batch_id, list(current_rows.values())
            )

            provider_rows[provider] = len(current_rows)
            total_rows += len(current_rows)
            inserted_rows += len(provider_inserts)
            updated_rows += len(provider_updates)
            deleted_rows += len(provider_deletes)
            unchanged_rows += provider_unchanged

        _insert_batch_items(sql_cfg, resolved_server, batch_items)
        _finalize_batch_log(
            sql_cfg,
            resolved_server,
            batch_id=batch_id,
            status="completed",
            inserted_rows=inserted_rows,
            updated_rows=updated_rows,
            deleted_rows=deleted_rows,
            unchanged_rows=unchanged_rows,
            error_message="",
        )
    except Exception as ex:
        _finalize_batch_log(
            sql_cfg,
            resolved_server,
            batch_id=batch_id,
            status="failed",
            inserted_rows=inserted_rows,
            updated_rows=updated_rows,
            deleted_rows=deleted_rows,
            unchanged_rows=unchanged_rows,
            error_message=str(ex),
        )
        raise

    return SqlServerWriteResult(
        batch_id=batch_id,
        total_rows=total_rows,
        provider_rows=provider_rows,
        inserted_rows=inserted_rows,
        updated_rows=updated_rows,
        deleted_rows=deleted_rows,
        unchanged_rows=unchanged_rows,
        script_path="",
    )


def initialize_sqlserver_schema(output_config: OutputConfig, ddl_path: Path | None = None) -> SqlServerSchemaResult:
    sql_cfg = output_config.sqlserver
    resolved_server = sql_cfg.resolve_server()
    if not resolved_server:
        raise ConfigError(
            "SQL Server connection is not configured. Set output.sqlserver.server or output.sqlserver.local_server."
        )

    if ddl_path is None:
        database_dir = Path(__file__).resolve().parents[3] / "database"
        ddl_paths = sorted(database_dir.glob("*.sql"))
        if not ddl_paths:
            raise ConfigError(f"No schema DDL files found in: {database_dir}")
    else:
        if not ddl_path.exists():
            raise ConfigError(f"Schema DDL file not found: {ddl_path}")
        ddl_paths = [ddl_path]

    with _open_connection(sql_cfg, resolved_server, database="master") as connection:
        cursor = connection.cursor()
        try:
            for script_path in ddl_paths:
                script_text = script_path.read_text(encoding="utf-8")
                for batch in _split_batches(script_text):
                    if batch.strip():
                        cursor.execute(batch)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return SqlServerSchemaResult(script_path=str(ddl_paths[-1]), server=resolved_server)


def _resolve_table_name(sql_cfg: SqlServerTargetConfig, provider: str) -> str:
    return sql_cfg.table_map.get(provider.lower(), "").strip()


def _open_connection(
    sql_cfg: SqlServerTargetConfig,
    resolved_server: str,
    database: str | None = None,
) -> pyodbc.Connection:
    connection_string = _build_connection_string(sql_cfg, resolved_server, database=database)
    try:
        connection = pyodbc.connect(connection_string, autocommit=False)
        if database and database.strip():
            cursor = connection.cursor()
            cursor.execute(f"USE [{database.replace(']', ']]')}]")
            cursor.close()
        return connection
    except pyodbc.Error as ex:
        raise ConfigError(f"Failed to connect to SQL Server: {ex}") from ex


def _build_connection_string(
    sql_cfg: SqlServerTargetConfig,
    resolved_server: str,
    database: str | None = None,
) -> str:
    parts = [f"DRIVER={{{sql_cfg.driver}}}", f"SERVER={resolved_server}"]
    if database:
        parts.append(f"DATABASE={database}")

    auth = sql_cfg.authentication.strip().lower()
    if auth == "integrated":
        parts.append("Trusted_Connection=yes")
    elif auth == "sql":
        password = os.getenv(sql_cfg.password_env, "") if sql_cfg.password_env else ""
        if not sql_cfg.username:
            raise ConfigError("SQL authentication requires output.sqlserver.username")
        if not password:
            raise ConfigError(
                "SQL authentication requires a non-empty password_env for output.sqlserver.password_env"
            )
        parts.append(f"UID={sql_cfg.username}")
        parts.append(f"PWD={password}")
    else:
        raise ConfigError(f"Unsupported SQL authentication mode: {sql_cfg.authentication}")

    parts.append("Encrypt=yes")
    if sql_cfg.trust_server_certificate:
        parts.append("TrustServerCertificate=yes")

    return ";".join(parts)


def _load_existing_rows(
    sql_cfg: SqlServerTargetConfig,
    resolved_server: str,
    table_name: str,
    vm_uuids: list[str],
) -> dict[str, dict]:
    if not vm_uuids:
        return {}

    quoted_table = _quote_table_name(table_name)
    columns = ", ".join([*(_quote_identifier(field) for field in EXPORT_FIELDS), "[IsDeleted]"])
    existing: dict[str, dict] = {}

    with _open_connection(sql_cfg, resolved_server, database=sql_cfg.database) as connection:
        cursor = connection.cursor()
        for chunk in _chunked(vm_uuids, 500):
            placeholders = ", ".join("?" for _ in chunk)
            query = (
                f"SELECT {columns} FROM {quoted_table} "
                f"WHERE [vm_uuid] IN ({placeholders}) ORDER BY [vm_uuid], [collected_at] DESC, [VirtualMachineId] DESC"
            )
            for db_row in cursor.execute(query, *chunk).fetchall():
                mapped = {field: value for field, value in zip([*EXPORT_FIELDS, "IsDeleted"], db_row)}
                vm_uuid = str(mapped.get("vm_uuid") or "")
                if vm_uuid and vm_uuid not in existing:
                    existing[vm_uuid] = mapped

    return existing


def _load_missing_active_rows(
    sql_cfg: SqlServerTargetConfig,
    resolved_server: str,
    table_name: str,
    current_vm_uuids: set[str],
) -> list[dict]:
    rows: list[dict] = []
    query = (
        f"SELECT [vm_uuid], [source_provider], [source_platform], [vmname], [collected_at] "
        f"FROM {_quote_table_name(table_name)} WHERE [IsDeleted] = 0"
    )

    with _open_connection(sql_cfg, resolved_server, database=sql_cfg.database) as connection:
        cursor = connection.cursor()
        for db_row in cursor.execute(query).fetchall():
            vm_uuid = str(db_row[0] or "")
            if not vm_uuid or vm_uuid in current_vm_uuids:
                continue
            rows.append(
                {
                    "vm_uuid": vm_uuid,
                    "source_provider": str(db_row[1] or ""),
                    "source_platform": str(db_row[2] or ""),
                    "vmname": str(db_row[3] or ""),
                    "collected_at": db_row[4],
                }
            )

    return rows


def _apply_changes(
    sql_cfg: SqlServerTargetConfig,
    resolved_server: str,
    table_name: str,
    batch_id: str,
    insert_rows: list[dict],
    update_rows: list[dict],
    delete_rows: list[dict],
) -> None:
    if not insert_rows and not update_rows and not delete_rows:
        return

    with _open_connection(sql_cfg, resolved_server, database=sql_cfg.database) as connection:
        cursor = connection.cursor()
        try:
            for batch in _chunked(insert_rows, 500):
                if batch:
                    _insert_rows(cursor, table_name, batch_id, batch)
            for batch in _chunked(update_rows, 500):
                if batch:
                    _update_rows(cursor, table_name, batch_id, batch)
            for batch in _chunked(delete_rows, 500):
                if batch:
                    _mark_deleted_rows(cursor, table_name, batch_id, batch)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def _sync_lifecycle_records(
    sql_cfg: SqlServerTargetConfig,
    resolved_server: str,
    table_name: str,
    batch_id: str,
    rows: list[dict],
) -> None:
    """Persist VM creation/description and timestamp actual power transitions."""
    schema = table_name.split(".", 1)[0]
    lifecycle = _quote_table_name(f"{schema}.VirtualMachineLifecycle")
    events = _quote_table_name(f"{schema}.VirtualMachinePowerEvent")
    with _open_connection(sql_cfg, resolved_server, database=sql_cfg.database) as connection:
        cursor = connection.cursor()
        try:
            for row in rows:
                vm_uuid = str(row.get("vm_uuid") or "").strip()
                state = str(row.get("powerstate") or "").strip().lower() or "unknown"
                observed_at = _convert_value("collected_at", row.get("collected_at"))
                created_at = _convert_value("creat_date", row.get("creat_date"))
                description = str(row.get("describ") or "").strip() or None
                current = cursor.execute(
                    f"SELECT CurrentPowerState FROM {lifecycle} WHERE vm_uuid=?", vm_uuid
                ).fetchone()
                event_type = _classify_power_transition(None if current is None else current[0], state)
                if current is None:
                    last_off = observed_at if state == "off" else None
                    last_on = observed_at if state == "on" else None
                    cursor.execute(
                        f"INSERT INTO {lifecycle}(vm_uuid,VmCreatedAt,AssetDescription,CurrentPowerState,"
                        "PowerStateChangedAt,LastPoweredOffAt,LastPoweredOnAt,SourceObservedAt,BatchId) "
                        "VALUES(?,?,?,?,?,?,?,?,?)",
                        vm_uuid, created_at, description, state, observed_at, last_off, last_on,
                        observed_at, batch_id,
                    )
                    cursor.execute(
                        f"INSERT INTO {events}(vm_uuid,PreviousPowerState,CurrentPowerState,EventType,OccurredAt,SourceObservedAt,BatchId) VALUES(?,NULL,?,'INITIAL_OBSERVATION',?,?,?)",
                        vm_uuid, state, observed_at, observed_at, batch_id,
                    )
                    continue
                previous = str(current[0] or "").strip().lower()
                changed = event_type == "STATE_CHANGED"
                cursor.execute(
                    f"UPDATE {lifecycle} SET VmCreatedAt=COALESCE(?,VmCreatedAt),AssetDescription=?,CurrentPowerState=?,"
                    "PowerStateChangedAt=CASE WHEN ?=1 THEN ? ELSE PowerStateChangedAt END,"
                    "LastPoweredOffAt=CASE WHEN ?=1 AND ?='off' THEN ? ELSE LastPoweredOffAt END,"
                    "LastPoweredOnAt=CASE WHEN ?=1 AND ?='on' THEN ? ELSE LastPoweredOnAt END,"
                    "SourceObservedAt=?,BatchId=?,UpdatedAt=SYSDATETIME() WHERE vm_uuid=?",
                    created_at, description, state, int(changed), observed_at,
                    int(changed), state, observed_at, int(changed), state, observed_at,
                    observed_at, batch_id, vm_uuid,
                )
                if changed:
                    cursor.execute(
                        f"INSERT INTO {events}(vm_uuid,PreviousPowerState,CurrentPowerState,EventType,OccurredAt,SourceObservedAt,BatchId) VALUES(?,?,?,'STATE_CHANGED',?,?,?)",
                        vm_uuid, previous, state, observed_at, observed_at, batch_id,
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def _classify_power_transition(previous: object, current: object) -> str | None:
    """Return the only event that should be emitted for an observed state."""
    current_state = str(current or "").strip().lower() or "unknown"
    if previous is None:
        return "INITIAL_OBSERVATION"
    previous_state = str(previous or "").strip().lower() or "unknown"
    return "STATE_CHANGED" if previous_state != current_state else None


def _insert_rows(cursor: pyodbc.Cursor, table_name: str, batch_id: str, rows: list[dict]) -> None:
    columns = ", ".join([_quote_identifier("BatchId"), *(_quote_identifier(name) for name in EXPORT_FIELDS)])
    placeholders = ", ".join("?" for _ in range(len(EXPORT_FIELDS) + 1))
    statement = f"INSERT INTO {_quote_table_name(table_name)} ({columns}) VALUES ({placeholders})"
    for row in rows:
        cursor.execute(statement, batch_id, *_row_to_parameters(row))


def _update_rows(cursor: pyodbc.Cursor, table_name: str, batch_id: str, rows: list[dict]) -> None:
    mutable_fields = [field for field in EXPORT_FIELDS if field != "vm_uuid"]
    assignments = ", ".join(
        [f"{_quote_identifier('BatchId')} = ?", *(f"{_quote_identifier(field)} = ?" for field in mutable_fields)]
    )
    statement = (
        f"UPDATE {_quote_table_name(table_name)} "
        f"SET {assignments}, [UpdatedAt] = sysdatetime(), [IsDeleted] = 0 WHERE [vm_uuid] = ?"
    )
    for row in rows:
        values = [batch_id, *(_convert_value(field, row.get(field)) for field in mutable_fields)]
        values.append(_convert_value("vm_uuid", row.get("vm_uuid")))
        cursor.execute(statement, *values)


def _dedupe_rows_by_vm_uuid(rows: list[dict]) -> dict[str, dict]:
    deduped: dict[str, dict] = {}
    for row in rows:
        vm_uuid = str(row.get("vm_uuid") or "").strip()
        if not vm_uuid:
            continue
        deduped[vm_uuid] = row
    return deduped


def _rows_differ(existing_row: dict, incoming_row: dict) -> bool:
    return bool(_get_changed_fields(existing_row, incoming_row))


def _get_changed_fields(existing_row: dict, incoming_row: dict) -> list[str]:
    changed_fields: list[str] = []
    if int(existing_row.get("IsDeleted") or 0) != 0:
        changed_fields.append("IsDeleted")
    for field in COMPARE_FIELDS:
        if _normalize_for_compare(field, existing_row.get(field)) != _normalize_for_compare(field, incoming_row.get(field)):
            changed_fields.append(field)
    return changed_fields


def _normalize_for_compare(field: str, value: object) -> object:
    if value in (None, ""):
        return None
    if field in {"sock", "vCore", "vTotalCore"}:
        return int(value)
    if field == "RAM_GB":
        return round(float(value), 2)
    if field in {"creat_date", "collected_at"}:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        text = str(value).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        return text
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _row_to_parameters(row: dict) -> tuple[object, ...]:
    return tuple(_convert_value(field, row.get(field)) for field in EXPORT_FIELDS)


def _convert_value(field: str, value: object) -> object:
    if value in (None, ""):
        return None

    if field in {"sock", "vCore", "vTotalCore"}:
        return int(value)

    if field == "RAM_GB":
        return float(value)

    if field in {"creat_date", "collected_at"}:
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return text

    return str(value)


def _quote_identifier(name: str) -> str:
    return f"[{name.replace(']', ']]')}]"


def _quote_table_name(name: str) -> str:
    parts = [part for part in name.split(".") if part]
    if len(parts) == 1:
        return _quote_identifier(parts[0])
    return ".".join(_quote_identifier(part) for part in parts)


def _split_batches(script_text: str) -> list[str]:
    batches: list[str] = []
    current: list[str] = []
    for line in script_text.splitlines():
        if line.strip().upper() == "GO":
            batch = "\n".join(current).strip()
            if batch:
                batches.append(batch)
            current = []
            continue
        current.append(line)
    tail = "\n".join(current).strip()
    if tail:
        batches.append(tail)
    return batches


def _create_batch_id(providers: list[str]) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    scope = "-".join(_sanitize_batch_token(provider) for provider in providers) if providers else "none"
    return f"{timestamp}_{scope}"[:50]


def _sanitize_batch_token(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value or ""))
    return normalized.strip("_") or "none"


def _create_batch_log(
    sql_cfg: SqlServerTargetConfig,
    resolved_server: str,
    batch_id: str,
    batch_scope: str,
    raw_record_count: int,
    processed_record_count: int,
) -> None:
    runner_host = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "unknown"
    runner_user = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
    statement = """
    INSERT INTO [ops].[SyncBatchLog]
    (
        [BatchId],
        [BatchScope],
        [Status],
        [BatchStartedAt],
        [RunnerHost],
        [RunnerUser],
        [RawRecordCount],
        [ProcessedRecordCount],
        [InsertedRows],
        [UpdatedRows],
        [DeletedRows],
        [UnchangedRows],
        [ErrorMessage]
    )
    VALUES (?, ?, ?, sysdatetime(), ?, ?, ?, ?, 0, 0, 0, 0, NULL)
    """
    with _open_connection(sql_cfg, resolved_server, database=sql_cfg.database) as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                statement,
                batch_id,
                batch_scope,
                "running",
                runner_host,
                runner_user,
                raw_record_count,
                processed_record_count,
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def _finalize_batch_log(
    sql_cfg: SqlServerTargetConfig,
    resolved_server: str,
    batch_id: str,
    status: str,
    inserted_rows: int,
    updated_rows: int,
    deleted_rows: int,
    unchanged_rows: int,
    error_message: str,
) -> None:
    statement = """
    UPDATE [ops].[SyncBatchLog]
    SET
        [Status] = ?,
        [BatchFinishedAt] = sysdatetime(),
        [InsertedRows] = ?,
        [UpdatedRows] = ?,
        [DeletedRows] = ?,
        [UnchangedRows] = ?,
        [DurationSeconds] = DATEDIFF(second, [BatchStartedAt], sysdatetime()),
        [ErrorMessage] = ?
    WHERE [BatchId] = ?
    """
    with _open_connection(sql_cfg, resolved_server, database=sql_cfg.database) as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                statement,
                status,
                inserted_rows,
                updated_rows,
                deleted_rows,
                unchanged_rows,
                error_message or None,
                batch_id,
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def _build_batch_item(
    batch_id: str,
    provider: str,
    table_name: str,
    row: dict,
    action: str,
    change_summary: str,
) -> dict[str, object]:
    return {
        "BatchId": batch_id,
        "SourceProvider": provider,
        "VmUuid": str(row.get("vm_uuid") or ""),
        "SourcePlatform": str(row.get("source_platform") or ""),
        "VmName": str(row.get("vmname") or ""),
        "TargetTable": table_name,
        "ActionType": action,
        "ChangeSummary": change_summary,
        "CollectedAt": _convert_value("collected_at", row.get("collected_at")),
    }


def _insert_batch_items(
    sql_cfg: SqlServerTargetConfig,
    resolved_server: str,
    items: list[dict[str, object]],
) -> None:
    if not items:
        return

    statement = """
    INSERT INTO [ops].[SyncBatchItem]
    (
        [BatchId],
        [SourceProvider],
        [VmUuid],
        [SourcePlatform],
        [VmName],
        [TargetTable],
        [ActionType],
        [ChangeSummary],
        [CollectedAt]
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _open_connection(sql_cfg, resolved_server, database=sql_cfg.database) as connection:
        cursor = connection.cursor()
        try:
            for batch in _chunked(items, 500):
                for item in batch:
                    cursor.execute(
                        statement,
                        item["BatchId"],
                        item["SourceProvider"],
                        item["VmUuid"],
                        item["SourcePlatform"],
                        item["VmName"],
                        item["TargetTable"],
                        item["ActionType"],
                        item["ChangeSummary"] or None,
                        item["CollectedAt"],
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def _mark_deleted_rows(cursor: pyodbc.Cursor, table_name: str, batch_id: str, rows: list[dict]) -> None:
    statement = (
        f"UPDATE {_quote_table_name(table_name)} "
        f"SET [BatchId] = ?, [UpdatedAt] = sysdatetime(), [IsDeleted] = 1 WHERE [vm_uuid] = ?"
    )
    for row in rows:
        cursor.execute(statement, batch_id, _convert_value("vm_uuid", row.get("vm_uuid")))


def _chunked(items: list[dict], size: int) -> Iterable[list[dict]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
