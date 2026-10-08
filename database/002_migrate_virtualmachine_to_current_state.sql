USE ExampleInventory;
GO

;WITH Ranked AS
(
    SELECT
        VirtualMachineId,
        ROW_NUMBER() OVER (
            PARTITION BY vm_uuid
            ORDER BY collected_at DESC, UpdatedAt DESC, VirtualMachineId DESC
        ) AS rn
    FROM src_nutanix.VirtualMachine
)
DELETE FROM Ranked WHERE rn > 1;
GO

;WITH Ranked AS
(
    SELECT
        VirtualMachineId,
        ROW_NUMBER() OVER (
            PARTITION BY vm_uuid
            ORDER BY collected_at DESC, UpdatedAt DESC, VirtualMachineId DESC
        ) AS rn
    FROM src_vmware.VirtualMachine
)
DELETE FROM Ranked WHERE rn > 1;
GO

IF EXISTS (
    SELECT 1
    FROM sys.key_constraints
    WHERE [name] = N'UQ_src_nutanix_VirtualMachine_vm_uuid_collected_at'
      AND [parent_object_id] = OBJECT_ID(N'src_nutanix.VirtualMachine')
)
BEGIN
    ALTER TABLE src_nutanix.VirtualMachine
    DROP CONSTRAINT UQ_src_nutanix_VirtualMachine_vm_uuid_collected_at;
END;
GO

IF EXISTS (
    SELECT 1
    FROM sys.key_constraints
    WHERE [name] = N'UQ_src_vmware_VirtualMachine_vm_uuid_collected_at'
      AND [parent_object_id] = OBJECT_ID(N'src_vmware.VirtualMachine')
)
BEGIN
    ALTER TABLE src_vmware.VirtualMachine
    DROP CONSTRAINT UQ_src_vmware_VirtualMachine_vm_uuid_collected_at;
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE [name] = N'UX_src_nutanix_VirtualMachine_vm_uuid'
      AND [object_id] = OBJECT_ID(N'src_nutanix.VirtualMachine')
)
BEGIN
    CREATE UNIQUE INDEX UX_src_nutanix_VirtualMachine_vm_uuid
        ON src_nutanix.VirtualMachine (vm_uuid);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE [name] = N'UX_src_vmware_VirtualMachine_vm_uuid'
      AND [object_id] = OBJECT_ID(N'src_vmware.VirtualMachine')
)
BEGIN
    CREATE UNIQUE INDEX UX_src_vmware_VirtualMachine_vm_uuid
        ON src_vmware.VirtualMachine (vm_uuid);
END;
GO
