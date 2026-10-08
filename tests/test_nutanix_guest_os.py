from vm_asset_inventory.providers.nutanix.collector import _map_vm
import pytest

@pytest.mark.parametrize('resources,expected',[
 ({'guest_tools':{'nutanix_guest_tools':{'guest_os_version':'linux:64:Ubuntu-22.04.4'}},'guest_os_id':'old'},'Ubuntu-22.04.4 (64-bit)'),
 ({'guest_tools':None,'guest_os_id':'Linux'},'Linux'),
 ({'guest_tools':{'nutanix_guest_tools':None}},''),
 ({'guest_tools':{'nutanix_guest_tools':{'guest_os_version':'custom OS'}}},'custom OS'),
])
def test_guest_os(resources,expected):
 assert _map_vm('test',{'status':{'resources':resources}}).osversion==expected

def test_spec_fallback():
 assert _map_vm('test',{'spec':{'resources':{'guest_os_id':'Ubuntu'}}}).osversion=='Ubuntu'
