/*
  ExampleInventory initial schema for vm_asset_inventory.
  Provider-split source tables + staging table.
*/

IF DB_ID(N'ExampleInventory') IS NULL
BEGIN
    CREATE DATABASE ExampleInventory;
END;
GO

USE ExampleInventory;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'stg')
    EXEC(N'CREATE SCHEMA stg');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'src_nutanix')
    EXEC(N'CREATE SCHEMA src_nutanix');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'src_vmware')
    EXEC(N'CREATE SCHEMA src_vmware');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'ops')
    EXEC(N'CREATE SCHEMA ops');
GO

IF OBJECT_ID(N'stg.VirtualMachineRaw', N'U') IS NULL
BEGIN
    CREATE TABLE stg.VirtualMachineRaw
    (
        StagingId bigint IDENTITY(1,1) NOT NULL,
        BatchId nvarchar(50) NULL,
        vm_uuid nvarchar(100) NOT NULL,
        source_provider nvarchar(50) NOT NULL,
        source_platform nvarchar(100) NOT NULL,
        cluster nvarchar(200) NULL,
        vmname nvarchar(200) NOT NULL,
        powerstate nvarchar(20) NOT NULL,
        sock int NULL,
        vCore int NULL,
        vTotalCore int NULL,
        RAM_GB decimal(10,2) NULL,
        disk_spec nvarchar(max) NULL,
        vlanname nvarchar(max) NULL,
        ip nvarchar(max) NULL,
        mac nvarchar(max) NULL,
        describ nvarchar(max) NULL,
        osversion nvarchar(200) NULL,
        creat_date datetime2(0) NULL,
        collected_at datetime2(0) NOT NULL,
        ImportedAt datetime2(0) NOT NULL CONSTRAINT DF_stg_VirtualMachineRaw_ImportedAt DEFAULT (sysdatetime()),
        ImportFileName nvarchar(260) NULL,
        ImportSourceType nvarchar(20) NULL,
        RowHash varchar(64) NULL,
        ValidationStatus nvarchar(20) NULL,
        ValidationMessage nvarchar(4000) NULL,
        CONSTRAINT PK_stg_VirtualMachineRaw PRIMARY KEY CLUSTERED (StagingId)
    );
END;
GO

IF OBJECT_ID(N'src_nutanix.VirtualMachine', N'U') IS NULL
BEGIN
    CREATE TABLE src_nutanix.VirtualMachine
    (
        VirtualMachineId bigint IDENTITY(1,1) NOT NULL,
        BatchId nvarchar(50) NULL,
        vm_uuid nvarchar(100) NOT NULL,
        source_provider nvarchar(50) NOT NULL CONSTRAINT DF_src_nutanix_VirtualMachine_source_provider DEFAULT (N'nutanix'),
        source_platform nvarchar(100) NOT NULL,
        cluster nvarchar(200) NULL,
        vmname nvarchar(200) NOT NULL,
        powerstate nvarchar(20) NOT NULL,
        sock int NULL,
        vCore int NULL,
        vTotalCore int NULL,
        RAM_GB decimal(10,2) NULL,
        disk_spec nvarchar(max) NULL,
        vlanname nvarchar(max) NULL,
        ip nvarchar(max) NULL,
        mac nvarchar(max) NULL,
        describ nvarchar(max) NULL,
        osversion nvarchar(200) NULL,
        creat_date datetime2(0) NULL,
        collected_at datetime2(0) NOT NULL,
        CreatedAt datetime2(0) NOT NULL CONSTRAINT DF_src_nutanix_VirtualMachine_CreatedAt DEFAULT (sysdatetime()),
        UpdatedAt datetime2(0) NOT NULL CONSTRAINT DF_src_nutanix_VirtualMachine_UpdatedAt DEFAULT (sysdatetime()),
        SourceRecordId nvarchar(200) NULL,
        IsDeleted bit NOT NULL CONSTRAINT DF_src_nutanix_VirtualMachine_IsDeleted DEFAULT (0),
        CONSTRAINT PK_src_nutanix_VirtualMachine PRIMARY KEY CLUSTERED (VirtualMachineId),
        CONSTRAINT CK_src_nutanix_VirtualMachine_source_provider CHECK (source_provider = N'nutanix')
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_src_nutanix_VirtualMachine_vmname' AND object_id = OBJECT_ID(N'src_nutanix.VirtualMachine'))
    CREATE INDEX IX_src_nutanix_VirtualMachine_vmname ON src_nutanix.VirtualMachine (vmname);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_src_nutanix_VirtualMachine_source_platform' AND object_id = OBJECT_ID(N'src_nutanix.VirtualMachine'))
    CREATE INDEX IX_src_nutanix_VirtualMachine_source_platform ON src_nutanix.VirtualMachine (source_platform);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_src_nutanix_VirtualMachine_collected_at' AND object_id = OBJECT_ID(N'src_nutanix.VirtualMachine'))
    CREATE INDEX IX_src_nutanix_VirtualMachine_collected_at ON src_nutanix.VirtualMachine (collected_at);
GO

IF OBJECT_ID(N'src_vmware.VirtualMachine', N'U') IS NULL
BEGIN
    CREATE TABLE src_vmware.VirtualMachine
    (
        VirtualMachineId bigint IDENTITY(1,1) NOT NULL,
        BatchId nvarchar(50) NULL,
        vm_uuid nvarchar(100) NOT NULL,
        source_provider nvarchar(50) NOT NULL CONSTRAINT DF_src_vmware_VirtualMachine_source_provider DEFAULT (N'vmware'),
        source_platform nvarchar(100) NOT NULL,
        cluster nvarchar(200) NULL,
        vmname nvarchar(200) NOT NULL,
        powerstate nvarchar(20) NOT NULL,
        sock int NULL,
        vCore int NULL,
        vTotalCore int NULL,
        RAM_GB decimal(10,2) NULL,
        disk_spec nvarchar(max) NULL,
        vlanname nvarchar(max) NULL,
        ip nvarchar(max) NULL,
        mac nvarchar(max) NULL,
        describ nvarchar(max) NULL,
        osversion nvarchar(200) NULL,
        creat_date datetime2(0) NULL,
        collected_at datetime2(0) NOT NULL,
        CreatedAt datetime2(0) NOT NULL CONSTRAINT DF_src_vmware_VirtualMachine_CreatedAt DEFAULT (sysdatetime()),
        UpdatedAt datetime2(0) NOT NULL CONSTRAINT DF_src_vmware_VirtualMachine_UpdatedAt DEFAULT (sysdatetime()),
        SourceRecordId nvarchar(200) NULL,
        IsDeleted bit NOT NULL CONSTRAINT DF_src_vmware_VirtualMachine_IsDeleted DEFAULT (0),
        CONSTRAINT PK_src_vmware_VirtualMachine PRIMARY KEY CLUSTERED (VirtualMachineId),
        CONSTRAINT CK_src_vmware_VirtualMachine_source_provider CHECK (source_provider = N'vmware')
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_src_vmware_VirtualMachine_vmname' AND object_id = OBJECT_ID(N'src_vmware.VirtualMachine'))
    CREATE INDEX IX_src_vmware_VirtualMachine_vmname ON src_vmware.VirtualMachine (vmname);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_src_vmware_VirtualMachine_source_platform' AND object_id = OBJECT_ID(N'src_vmware.VirtualMachine'))
    CREATE INDEX IX_src_vmware_VirtualMachine_source_platform ON src_vmware.VirtualMachine (source_platform);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_src_vmware_VirtualMachine_collected_at' AND object_id = OBJECT_ID(N'src_vmware.VirtualMachine'))
    CREATE INDEX IX_src_vmware_VirtualMachine_collected_at ON src_vmware.VirtualMachine (collected_at);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_stg_VirtualMachineRaw_vmname' AND object_id = OBJECT_ID(N'stg.VirtualMachineRaw'))
    CREATE INDEX IX_stg_VirtualMachineRaw_vmname ON stg.VirtualMachineRaw (vmname);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_stg_VirtualMachineRaw_collected_at' AND object_id = OBJECT_ID(N'stg.VirtualMachineRaw'))
    CREATE INDEX IX_stg_VirtualMachineRaw_collected_at ON stg.VirtualMachineRaw (collected_at);
GO

IF OBJECT_ID(N'ops.SyncBatchLog', N'U') IS NULL
BEGIN
    CREATE TABLE ops.SyncBatchLog
    (
        BatchId nvarchar(50) NOT NULL,
        BatchScope nvarchar(100) NOT NULL,
        Status nvarchar(20) NOT NULL,
        BatchStartedAt datetime2(0) NOT NULL,
        BatchFinishedAt datetime2(0) NULL,
        RunnerHost nvarchar(128) NULL,
        RunnerUser nvarchar(128) NULL,
        DurationSeconds int NULL,
        RawRecordCount int NOT NULL,
        ProcessedRecordCount int NOT NULL,
        InsertedRows int NOT NULL CONSTRAINT DF_ops_SyncBatchLog_InsertedRows DEFAULT (0),
        UpdatedRows int NOT NULL CONSTRAINT DF_ops_SyncBatchLog_UpdatedRows DEFAULT (0),
        DeletedRows int NOT NULL CONSTRAINT DF_ops_SyncBatchLog_DeletedRows DEFAULT (0),
        UnchangedRows int NOT NULL CONSTRAINT DF_ops_SyncBatchLog_UnchangedRows DEFAULT (0),
        ErrorMessage nvarchar(4000) NULL,
        CreatedAt datetime2(0) NOT NULL CONSTRAINT DF_ops_SyncBatchLog_CreatedAt DEFAULT (sysdatetime()),
        CONSTRAINT PK_ops_SyncBatchLog PRIMARY KEY CLUSTERED (BatchId)
    );
END;
GO

IF OBJECT_ID(N'ops.SyncBatchItem', N'U') IS NULL
BEGIN
    CREATE TABLE ops.SyncBatchItem
    (
        SyncBatchItemId bigint IDENTITY(1,1) NOT NULL,
        BatchId nvarchar(50) NOT NULL,
        SourceProvider nvarchar(50) NOT NULL,
        VmUuid nvarchar(100) NOT NULL,
        SourcePlatform nvarchar(100) NULL,
        VmName nvarchar(200) NULL,
        TargetTable nvarchar(128) NOT NULL,
        ActionType nvarchar(20) NOT NULL,
        ChangeSummary nvarchar(1000) NULL,
        CollectedAt datetime2(0) NULL,
        RecordedAt datetime2(0) NOT NULL CONSTRAINT DF_ops_SyncBatchItem_RecordedAt DEFAULT (sysdatetime()),
        CONSTRAINT PK_ops_SyncBatchItem PRIMARY KEY CLUSTERED (SyncBatchItemId),
        CONSTRAINT FK_ops_SyncBatchItem_BatchId FOREIGN KEY (BatchId) REFERENCES ops.SyncBatchLog (BatchId)
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ops_SyncBatchLog_BatchStartedAt' AND object_id = OBJECT_ID(N'ops.SyncBatchLog'))
    CREATE INDEX IX_ops_SyncBatchLog_BatchStartedAt ON ops.SyncBatchLog (BatchStartedAt DESC);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ops_SyncBatchItem_BatchId' AND object_id = OBJECT_ID(N'ops.SyncBatchItem'))
    CREATE INDEX IX_ops_SyncBatchItem_BatchId ON ops.SyncBatchItem (BatchId, ActionType);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ops_SyncBatchItem_VmUuid' AND object_id = OBJECT_ID(N'ops.SyncBatchItem'))
    CREATE INDEX IX_ops_SyncBatchItem_VmUuid ON ops.SyncBatchItem (VmUuid);
GO

IF OBJECT_ID(N'ops.vwSyncBatchCurrentVmRelation', N'V') IS NULL
    EXEC(N'
    CREATE VIEW ops.vwSyncBatchCurrentVmRelation
    AS
    SELECT
        log.BatchId,
        log.BatchScope,
        log.Status,
        log.BatchStartedAt,
        log.BatchFinishedAt,
        log.RunnerHost,
        log.RunnerUser,
        log.DurationSeconds,
        log.RawRecordCount,
        log.ProcessedRecordCount,
        log.InsertedRows,
        log.UpdatedRows,
        log.DeletedRows,
        log.UnchangedRows,
        item.SyncBatchItemId,
        item.SourceProvider,
        item.VmUuid,
        item.SourcePlatform,
        item.VmName,
        item.TargetTable,
        item.ActionType,
        item.ChangeSummary,
        item.CollectedAt,
        vm.VirtualMachineId,
        vm.BatchId AS CurrentRowBatchId,
        vm.powerstate,
        vm.RAM_GB,
        vm.ip,
        vm.mac,
        vm.UpdatedAt,
        vm.IsDeleted
    FROM ops.SyncBatchLog AS log
    INNER JOIN ops.SyncBatchItem AS item
        ON item.BatchId = log.BatchId
    LEFT JOIN src_nutanix.VirtualMachine AS vm
        ON item.SourceProvider = N''nutanix''
       AND vm.vm_uuid = item.VmUuid
    WHERE item.SourceProvider = N''nutanix''
    UNION ALL
    SELECT
        log.BatchId,
        log.BatchScope,
        log.Status,
        log.BatchStartedAt,
        log.BatchFinishedAt,
        log.RunnerHost,
        log.RunnerUser,
        log.DurationSeconds,
        log.RawRecordCount,
        log.ProcessedRecordCount,
        log.InsertedRows,
        log.UpdatedRows,
        log.DeletedRows,
        log.UnchangedRows,
        item.SyncBatchItemId,
        item.SourceProvider,
        item.VmUuid,
        item.SourcePlatform,
        item.VmName,
        item.TargetTable,
        item.ActionType,
        item.ChangeSummary,
        item.CollectedAt,
        vm.VirtualMachineId,
        vm.BatchId AS CurrentRowBatchId,
        vm.powerstate,
        vm.RAM_GB,
        vm.ip,
        vm.mac,
        vm.UpdatedAt,
        vm.IsDeleted
    FROM ops.SyncBatchLog AS log
    INNER JOIN ops.SyncBatchItem AS item
        ON item.BatchId = log.BatchId
    LEFT JOIN src_vmware.VirtualMachine AS vm
        ON item.SourceProvider = N''vmware''
       AND vm.vm_uuid = item.VmUuid
    WHERE item.SourceProvider = N''vmware''
    ');
GO

PRINT N'ExampleInventory schema created or already exists.';
GO
