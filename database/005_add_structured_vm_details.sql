USE ExampleInventory;
GO
IF COL_LENGTH(N'src_nutanix.VirtualMachine',N'network_json') IS NULL ALTER TABLE src_nutanix.VirtualMachine ADD network_json nvarchar(max) NULL;
IF COL_LENGTH(N'src_nutanix.VirtualMachine',N'storage_json') IS NULL ALTER TABLE src_nutanix.VirtualMachine ADD storage_json nvarchar(max) NULL;
IF COL_LENGTH(N'src_nutanix.VirtualMachine',N'vlanid') IS NULL ALTER TABLE src_nutanix.VirtualMachine ADD vlanid nvarchar(max) NULL;
IF COL_LENGTH(N'src_vmware.VirtualMachine',N'network_json') IS NULL ALTER TABLE src_vmware.VirtualMachine ADD network_json nvarchar(max) NULL;
IF COL_LENGTH(N'src_vmware.VirtualMachine',N'storage_json') IS NULL ALTER TABLE src_vmware.VirtualMachine ADD storage_json nvarchar(max) NULL;
IF COL_LENGTH(N'src_vmware.VirtualMachine',N'vlanid') IS NULL ALTER TABLE src_vmware.VirtualMachine ADD vlanid nvarchar(max) NULL;
GO
IF NOT EXISTS(SELECT 1 FROM sys.check_constraints WHERE name=N'CK_src_nutanix_VM_network_json') ALTER TABLE src_nutanix.VirtualMachine ADD CONSTRAINT CK_src_nutanix_VM_network_json CHECK(network_json IS NULL OR ISJSON(network_json)=1);
IF NOT EXISTS(SELECT 1 FROM sys.check_constraints WHERE name=N'CK_src_nutanix_VM_storage_json') ALTER TABLE src_nutanix.VirtualMachine ADD CONSTRAINT CK_src_nutanix_VM_storage_json CHECK(storage_json IS NULL OR ISJSON(storage_json)=1);
IF NOT EXISTS(SELECT 1 FROM sys.check_constraints WHERE name=N'CK_src_vmware_VM_network_json') ALTER TABLE src_vmware.VirtualMachine ADD CONSTRAINT CK_src_vmware_VM_network_json CHECK(network_json IS NULL OR ISJSON(network_json)=1);
IF NOT EXISTS(SELECT 1 FROM sys.check_constraints WHERE name=N'CK_src_vmware_VM_storage_json') ALTER TABLE src_vmware.VirtualMachine ADD CONSTRAINT CK_src_vmware_VM_storage_json CHECK(storage_json IS NULL OR ISJSON(storage_json)=1);
GO
