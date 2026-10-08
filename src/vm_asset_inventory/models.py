from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json


EXPORT_FIELDS = [
    "vm_uuid",
    "source_provider",
    "source_platform",
    "cluster",
    "vmname",
    "powerstate",
    "sock",
    "vCore",
    "vTotalCore",
    "RAM_GB",
    "disk_spec",
    "vlanname",
    "vlanid",
    "ip",
    "mac",
    "describ",
    "osversion",
    "creat_date",
    "collected_at",
    "network_json",
    "storage_json",
]


@dataclass
class VMAssetRecord:
    source_provider: str
    source_platform: str
    cluster: str
    host: str
    vmname: str
    vm_uuid: str
    powerstate: str
    sock: int
    vCore: int
    vTotalCore: int
    RAM: int
    Disk: float
    vlanname: str
    vlanid: str
    ip: str
    mac: str
    disk_spec: str
    describ: str
    osversion: str
    creat_date: str
    collected_at: str
    network_details: list[dict] | None = None
    storage_details: list[dict] | None = None

    @staticmethod
    def now_string() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return {
            "source_provider": self.source_provider,
            "source_platform": self.source_platform,
            "cluster": self.cluster,
            "host": self.host,
            "vmname": self.vmname,
            "vm_uuid": self.vm_uuid,
            "powerstate": self.powerstate,
            "sock": self.sock,
            "vCore": self.vCore,
            "vTotalCore": self.vTotalCore,
            "RAM": self.RAM,
            "Disk": self.Disk,
            "vlanname": self.vlanname,
            "vlanid": self.vlanid,
            "ip": self.ip,
            "mac": self.mac,
            "disk_spec": self.disk_spec,
            "describ": self.describ,
            "osversion": self.osversion,
            "creat_date": self.creat_date,
            "collected_at": self.collected_at,
            "network_json": json.dumps(self.network_details or [], ensure_ascii=False, separators=(",", ":")),
            "storage_json": json.dumps(self.storage_details or [], ensure_ascii=False, separators=(",", ":")),
        }

    def to_export_dict(self) -> dict:
        row = self.to_dict()
        out: dict = {}
        for key in EXPORT_FIELDS:
            if key == "RAM_GB":
                value = round(float(self.RAM) / 1024.0, 2)
            else:
                value = row.get(key, "")
            if isinstance(value, str):
                out[key] = _sanitize_text(value)
            else:
                out[key] = value

        # Keep provider token normalized for current and future providers.
        out["source_provider"] = str(out.get("source_provider", "")).strip().lower()
        return out


def _sanitize_text(value: str) -> str:
    # Avoid embedded newlines/control chars causing CSV readers to misinterpret rows.
    text = (value or "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = text.replace("\t", " ").replace("\x00", "")
    text = text.replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
    return " ".join(text.split())
