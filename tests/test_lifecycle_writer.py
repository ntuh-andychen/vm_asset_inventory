from pathlib import Path

from vm_asset_inventory.persistence.sqlserver import _classify_power_transition


ROOT = Path(__file__).resolve().parents[1]


def test_lifecycle_schema_has_current_history_and_events() -> None:
    sql = (ROOT / "database" / "006_add_vm_lifecycle_tracking.sql").read_text(encoding="utf-8")
    assert "VirtualMachineLifecycleHistory" in sql
    assert "VirtualMachinePowerEvent" in sql
    assert "SYSTEM_VERSIONING=ON" in sql


def test_writer_only_creates_event_for_changed_state() -> None:
    code = (ROOT / "src" / "vm_asset_inventory" / "persistence" / "sqlserver.py").read_text(encoding="utf-8")
    assert 'changed = event_type == "STATE_CHANGED"' in code
    assert "if changed:" in code
    assert "'STATE_CHANGED'" in code


def test_power_transition_paths() -> None:
    assert _classify_power_transition(None, "off") == "INITIAL_OBSERVATION"
    assert _classify_power_transition("off", "off") is None
    assert _classify_power_transition("off", "on") == "STATE_CHANGED"
    assert _classify_power_transition("on", "off") == "STATE_CHANGED"
