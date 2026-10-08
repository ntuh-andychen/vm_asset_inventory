from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from tenacity import RetryError

from vm_asset_inventory.models import VMAssetRecord
from vm_asset_inventory.settings import NutanixEndpointConfig, ProxyConfig
from vm_asset_inventory.utils.normalize import join_unique, to_float, to_int

from .client import NutanixClient


@dataclass
class ConnectionTestResult:
    provider: str
    endpoint: str
    success: bool
    message: str


def _parse_datetime(raw: str) -> str:
    if not raw:
        return ""
    text = raw.rstrip("Z")
    if "." in text:
        text = text.split(".", 1)[0]
    try:
        dt = datetime.fromisoformat(text)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ""


def collect_nutanix(endpoints: list[NutanixEndpointConfig], proxy_config: ProxyConfig | None = None) -> list[VMAssetRecord]:
    records: list[VMAssetRecord] = []

    for ep in endpoints:
        proxies: dict[str, str] = {}
        if proxy_config:
            proxies = proxy_config.resolve_requests_proxies(ep.proxy_feature)

        client = NutanixClient(
            base_url=ep.base_url,
            username=ep.username,
            password=ep.password,
            verify_ssl=ep.verify_ssl,
            ca_bundle=ep.ca_bundle,
            timeout=30,
            api_limit=ep.api_limit,
            request_delay=ep.request_delay,
            proxies=proxies,
        )
        try:
            entities = client.fetch_all_vms()
            for vm in entities:
                records.append(_map_vm(ep.name, vm))
        finally:
            client.close()

    return records


def test_nutanix_connections(
    endpoints: list[NutanixEndpointConfig],
    proxy_config: ProxyConfig | None = None,
) -> list[ConnectionTestResult]:
    results: list[ConnectionTestResult] = []

    for ep in endpoints:
        proxies: dict[str, str] = {}
        if proxy_config:
            proxies = proxy_config.resolve_requests_proxies(ep.proxy_feature)

        client = NutanixClient(
            base_url=ep.base_url,
            username=ep.username,
            password=ep.password,
            verify_ssl=ep.verify_ssl,
            ca_bundle=ep.ca_bundle,
            timeout=30,
            api_limit=ep.api_limit,
            request_delay=ep.request_delay,
            proxies=proxies,
        )

        try:
            client.test_connection()
            results.append(
                ConnectionTestResult(
                    provider="nutanix",
                    endpoint=ep.name,
                    success=True,
                    message="ok",
                )
            )
        except RetryError as ex:
            last_ex = ex.last_attempt.exception() if ex.last_attempt else ex
            msg = str(last_ex or ex)
            results.append(
                ConnectionTestResult(
                    provider="nutanix",
                    endpoint=ep.name,
                    success=False,
                    message=msg,
                )
            )
        except Exception as ex:
            results.append(
                ConnectionTestResult(
                    provider="nutanix",
                    endpoint=ep.name,
                    success=False,
                    message=str(ex),
                )
            )
        finally:
            client.close()

    return results


def _map_vm(platform_name: str, vm: dict) -> VMAssetRecord:
    spec = vm.get("spec", {})
    status = vm.get("status", {})
    metadata = vm.get("metadata", {})

    spec_res = spec.get("resources", {})
    st_res = status.get("resources", {})

    vmname = spec.get("name") or status.get("name") or ""
    vm_uuid = metadata.get("uuid", "")
    cluster = (spec.get("cluster_reference") or {}).get("name") or (status.get("cluster_reference") or {}).get("name") or ""

    raw_state = str(st_res.get("power_state", "")).lower()
    powerstate = "on" if raw_state in {"on", "running", "power_on"} else "off"

    num_sockets = to_int(st_res.get("num_sockets") or spec_res.get("num_sockets"), 0)
    cores_per_socket = to_int(st_res.get("num_vcpus_per_socket") or spec_res.get("num_vcpus_per_socket"), 0)
    total_core = to_int(st_res.get("num_vcpus") or spec_res.get("num_vcpus"), 0)
    if total_core == 0:
        total_core = num_sockets * cores_per_socket

    memory_mib = to_int(st_res.get("memory_size_mib") or spec_res.get("memory_size_mib"), 0)

    macs: list[str] = []
    ips: list[str] = []
    vlan_names: list[str] = []
    vlan_ids: list[str] = []
    disk_specs: list[str] = []
    network_details: list[dict] = []
    storage_details: list[dict] = []
    total_disk_gb = 0.0

    for nic_pos, nic in enumerate(st_res.get("nic_list", [])):
        mac = nic.get("mac_address")
        if mac:
            macs.append(mac)

        subnet_ref = nic.get("subnet_reference") or {}
        if subnet_ref.get("name"):
            vlan_names.append(str(subnet_ref.get("name")))
        if subnet_ref.get("uuid"):
            vlan_ids.append(str(subnet_ref.get("uuid")))

        nic_ips: list[str] = []
        for ep in nic.get("ip_endpoint_list", []):
            ip = str(ep.get("ip", ""))
            if ip and ":" not in ip:
                ips.append(ip)
                nic_ips.append(ip)
        network_details.append({
            "adapter_key": str(nic.get("uuid") or nic_pos),
            "mac": str(mac or ""),
            "vlan_name": str(subnet_ref.get("name") or ""),
            "vlan_id": str(subnet_ref.get("uuid") or ""),
            "ip_addresses": nic_ips,
        })

    for disk_pos, d in enumerate(st_res.get("disk_list", [])):
        device_props = d.get("device_properties", {}) or {}
        device_type = str(device_props.get("device_type", "") or "").upper()
        if device_type == "CDROM":
            disk_specs.append(f"CD-ROM{disk_pos}")
            storage_details.append({"device_key": str(disk_pos), "device_type": "CD-ROM", "label": f"CD-ROM{disk_pos}", "size_gb": None, "provisioning": ""})
            continue

        size_mib = to_float(d.get("disk_size_mib"), 0.0)
        total_disk_gb += (size_mib / 1024.0)
        addr = device_props.get("disk_address", {})
        device_bus = str(addr.get("device_bus", "disk") or "disk")
        device_index = str(disk_pos)
        disk_specs.append(
            f"{device_bus}{device_index}={round(size_mib/1024.0,2)}GB"
        )
        storage_details.append({"device_key": str(disk_pos), "device_type": "DISK", "label": f"{device_bus}{device_index}", "size_gb": round(size_mib/1024.0, 2), "provisioning": ""})

    describ = str(spec.get("description") or status.get("description") or "")
    guest_tools = (st_res.get("guest_tools") or {}).get("nutanix_guest_tools") or {}
    osversion = str(guest_tools.get("guest_os_version") or st_res.get("guest_os_id") or spec_res.get("guest_os_id") or "").strip()
    # NGT reports e.g. linux:64:Ubuntu-22.04.4; retain the reported edition.
    parts = osversion.split(":", 2)
    if len(parts) == 3 and parts[1] in {"32", "64"} and parts[2]:
        osversion = f"{parts[2]} ({parts[1]}-bit)"

    return VMAssetRecord(
        source_provider="nutanix",
        source_platform=platform_name,
        cluster=cluster,
        host="",
        vmname=vmname,
        vm_uuid=vm_uuid,
        powerstate=powerstate,
        sock=num_sockets,
        vCore=cores_per_socket,
        vTotalCore=total_core,
        RAM=memory_mib,
        Disk=round(total_disk_gb, 2),
        vlanname=join_unique(vlan_names, delimiter=":"),
        vlanid=join_unique(vlan_ids, delimiter=":"),
        ip=join_unique(ips, delimiter=":"),
        mac=join_unique(macs, delimiter=";"),
        disk_spec=join_unique(disk_specs, delimiter=";"),
        describ=describ,
        osversion=osversion,
        creat_date=_parse_datetime(str(metadata.get("creation_time", ""))),
        collected_at=VMAssetRecord.now_string(),
        network_details=network_details,
        storage_details=storage_details,
    )
