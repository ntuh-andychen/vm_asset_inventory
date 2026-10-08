from __future__ import annotations

from datetime import datetime
from math import ceil
from dataclasses import dataclass

from pyVmomi import vim

from vm_asset_inventory.models import VMAssetRecord
from vm_asset_inventory.settings import VMwareEndpointConfig
from vm_asset_inventory.utils.normalize import join_unique

from .client import VMwareClient


@dataclass
class ConnectionTestResult:
    provider: str
    endpoint: str
    success: bool
    message: str


def collect_vmware(endpoints: list[VMwareEndpointConfig]) -> list[VMAssetRecord]:
    records: list[VMAssetRecord] = []

    for ep in endpoints:
        client = VMwareClient(
            host=ep.host,
            username=ep.username,
            password=ep.password,
            port=ep.port,
            verify_ssl=ep.verify_ssl,
            ca_bundle=ep.ca_bundle,
        )
        try:
            client.connect()
            for vm in client.list_vms():
                records.append(_map_vm(ep.name, vm))
        finally:
            client.disconnect()

    return records


def test_vmware_connections(endpoints: list[VMwareEndpointConfig]) -> list[ConnectionTestResult]:
    results: list[ConnectionTestResult] = []

    for ep in endpoints:
        client = VMwareClient(
            host=ep.host,
            username=ep.username,
            password=ep.password,
            port=ep.port,
            verify_ssl=ep.verify_ssl,
            ca_bundle=ep.ca_bundle,
        )
        try:
            client.connect()
            results.append(
                ConnectionTestResult(
                    provider="vmware",
                    endpoint=ep.name,
                    success=True,
                    message="ok",
                )
            )
        except Exception as ex:
            results.append(
                ConnectionTestResult(
                    provider="vmware",
                    endpoint=ep.name,
                    success=False,
                    message=str(ex),
                )
            )
        finally:
            client.disconnect()

    return results


def _map_vm(platform_name: str, vm: object) -> VMAssetRecord:
    config = getattr(vm, "config", None)
    summary = getattr(vm, "summary", None)
    guest = getattr(vm, "guest", None)
    runtime = getattr(vm, "runtime", None)

    cluster = ""
    host = ""
    if runtime and getattr(runtime, "host", None):
        host_obj = runtime.host
        host = getattr(host_obj, "name", "")
        parent = getattr(host_obj, "parent", None)
        cluster = getattr(parent, "name", "") if parent else ""

    vmname = getattr(config, "name", "") if config else getattr(vm, "name", "")
    vm_uuid = ""
    if config:
        vm_uuid = getattr(config, "instanceUuid", "") or getattr(config, "uuid", "") or ""

    raw_power = str(getattr(runtime, "powerState", "")).lower() if runtime else ""
    powerstate = "on" if raw_power in {"poweredon", "on", "running"} else "off"

    num_cpu = int(getattr(getattr(config, "hardware", None), "numCPU", 0) or 0)
    cores_per_socket = int(getattr(getattr(config, "hardware", None), "numCoresPerSocket", 0) or 0)
    # Some vCenter records expose a stale cores-per-socket value greater than
    # numCPU.  Keep the canonical contract socket * vCore = vTotalCore.
    if num_cpu > 0 and (cores_per_socket <= 0 or cores_per_socket > num_cpu):
        cores_per_socket = num_cpu
    sock = int(ceil(num_cpu / cores_per_socket)) if cores_per_socket > 0 else 0

    memory_mb = int(getattr(getattr(config, "hardware", None), "memoryMB", 0) or 0)

    macs: list[str] = []
    ips: list[str] = []
    vlan_names: list[str] = []
    vlan_ids: list[str] = []
    disk_specs: list[str] = []
    network_details: list[dict] = []
    storage_details: list[dict] = []
    total_disk_gb = 0.0
    cdrom_idx = 0

    if config and getattr(config, "hardware", None):
        for dev in config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualEthernetCard):
                mac = getattr(dev, "macAddress", "")
                if mac:
                    macs.append(mac)

                backing = getattr(dev, "backing", None)
                net_name = getattr(getattr(backing, "network", None), "name", "") or getattr(getattr(dev, "deviceInfo", None), "summary", "")
                if net_name:
                    vlan_names.append(str(net_name))

                port_info = getattr(backing, "port", None)
                nic_vlan_ids: list[str] = []
                if port_info:
                    if getattr(port_info, "portgroupKey", None):
                        vlan_ids.append(str(port_info.portgroupKey))
                        nic_vlan_ids.append(str(port_info.portgroupKey))
                    if getattr(port_info, "switchUuid", None):
                        vlan_ids.append(str(port_info.switchUuid))
                        nic_vlan_ids.append(str(port_info.switchUuid))
                network_details.append({
                    "adapter_key": str(getattr(dev, "key", "") or len(network_details)),
                    "mac": str(mac or ""),
                    "vlan_name": str(net_name or ""),
                    "vlan_id": ":".join(nic_vlan_ids),
                    "ip_addresses": [],
                })

            if isinstance(dev, vim.vm.device.VirtualDisk):
                kb = float(getattr(dev, "capacityInKB", 0) or 0)
                gb = kb / 1024.0 / 1024.0
                total_disk_gb += gb
                label = getattr(getattr(dev, "deviceInfo", None), "label", "disk")
                backing = getattr(dev, "backing", None)
                thin = getattr(backing, "thinProvisioned", None)
                disk_type = "thin" if thin is True else ("thick" if thin is False else "unknown")
                disk_specs.append(f"{label}={round(gb,2)}GB({disk_type})")
                storage_details.append({"device_key": str(getattr(dev, "key", "") or len(storage_details)), "device_type": "DISK", "label": str(label), "size_gb": round(gb, 2), "provisioning": disk_type})

            if isinstance(dev, vim.vm.device.VirtualCdrom):
                disk_specs.append(f"CD-ROM{cdrom_idx}")
                storage_details.append({"device_key": str(getattr(dev, "key", "") or cdrom_idx), "device_type": "CD-ROM", "label": f"CD-ROM{cdrom_idx}", "size_gb": None, "provisioning": ""})
                cdrom_idx += 1

    if guest and getattr(guest, "net", None):
        for net in guest.net:
            guest_mac = str(getattr(net, "macAddress", "") or "").lower()
            for ip in (getattr(net, "ipAddress", None) or []):
                ip_text = str(ip)
                if ip_text and ":" not in ip_text:
                    ips.append(ip_text)
                    for adapter in network_details:
                        if guest_mac and str(adapter.get("mac") or "").lower() == guest_mac:
                            adapter["ip_addresses"].append(ip_text)

    osversion = ""
    if guest:
        osversion = getattr(guest, "guestFullName", "") or ""
    if not osversion and config:
        osversion = getattr(config, "guestFullName", "") or ""

    create_date = ""
    if config and getattr(config, "createDate", None):
        create_date = config.createDate.strftime("%Y-%m-%d %H:%M:%S")

    describ = getattr(config, "annotation", "") if config else ""

    return VMAssetRecord(
        source_provider="vmware",
        source_platform=platform_name,
        cluster=cluster,
        host=host,
        vmname=vmname,
        vm_uuid=vm_uuid,
        powerstate=powerstate,
        sock=sock,
        vCore=cores_per_socket,
        vTotalCore=num_cpu,
        RAM=memory_mb,
        Disk=round(total_disk_gb, 2),
        vlanname=join_unique(vlan_names, delimiter=":"),
        vlanid=join_unique(vlan_ids, delimiter=":"),
        ip=join_unique(ips, delimiter=":"),
        mac=join_unique(macs, delimiter=";"),
        disk_spec=join_unique(disk_specs, delimiter=";"),
        describ=str(describ or ""),
        osversion=osversion,
        creat_date=create_date,
        collected_at=VMAssetRecord.now_string(),
        network_details=network_details,
        storage_details=storage_details,
    )
