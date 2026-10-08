import json

from vm_asset_inventory.models import VMAssetRecord
from vm_asset_inventory.providers.vmware.collector import _map_vm


def test_structured_details_are_exported_as_json() -> None:
    record = VMAssetRecord(
        source_provider="vmware", source_platform="vc", cluster="c", host="h",
        vmname="vm", vm_uuid="uuid", powerstate="on", sock=2, vCore=4,
        vTotalCore=8, RAM=8192, Disk=100, vlanname="server", vlanid="dvpg-1",
        ip="192.0.2.151", mac="00:11:22:33:44:55", disk_spec="disk=100GB",
        describ="", osversion="Linux", creat_date="", collected_at="2026-08-25 10:00:00",
        network_details=[{"adapter_key":"1","mac":"00:11:22:33:44:55","vlan_name":"server","vlan_id":"dvpg-1","ip_addresses":["192.0.2.151"]}],
        storage_details=[{"device_key":"2","device_type":"DISK","label":"disk","size_gb":100,"provisioning":"thin"}],
    )
    row = record.to_export_dict()
    assert json.loads(row["network_json"])[0]["ip_addresses"] == ["192.0.2.151"]
    assert json.loads(row["storage_json"])[0]["provisioning"] == "thin"


def test_vmware_inconsistent_socket_data_is_normalized() -> None:
    class Obj:
        pass

    vm = Obj(); vm.config = Obj(); vm.summary = Obj(); vm.guest = None; vm.runtime = None
    vm.config.name = "test"; vm.config.instanceUuid = "uuid"; vm.config.uuid = "uuid"
    vm.config.hardware = Obj(); vm.config.hardware.numCPU = 1
    vm.config.hardware.numCoresPerSocket = 4; vm.config.hardware.memoryMB = 1024
    vm.config.hardware.device = []; vm.config.guestFullName = "Linux"
    vm.config.createDate = None; vm.config.annotation = ""
    record = _map_vm("vcenter", vm)
    assert record.sock * record.vCore == record.vTotalCore == 1
