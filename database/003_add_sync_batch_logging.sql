USE ExampleInventory;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'ops')
    EXEC(N'CREATE SCHEMA ops');
GO

IF COL_LENGTH(N'stg.VirtualMachineRaw', N'BatchId') IS NOT NULL
    ALTER TABLE stg.VirtualMachineRaw ALTER COLUMN BatchId nvarchar(50) NULL;
GO

IF COL_LENGTH(N'src_nutanix.VirtualMachine', N'BatchId') IS NOT NULL
    ALTER TABLE src_nutanix.VirtualMachine ALTER COLUMN BatchId nvarchar(50) NULL;
GO

IF COL_LENGTH(N'src_vmware.VirtualMachine', N'BatchId') IS NOT NULL
    ALTER TABLE src_vmware.VirtualMachine ALTER COLUMN BatchId nvarchar(50) NULL;
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
        RawRecordCount int NOT NULL,
        ProcessedRecordCount int NOT NULL,
        InsertedRows int NOT NULL CONSTRAINT DF_ops_SyncBatchLog_InsertedRows DEFAULT (0),
        UpdatedRows int NOT NULL CONSTRAINT DF_ops_SyncBatchLog_UpdatedRows DEFAULT (0),
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
        log.RawRecordCount,
        log.ProcessedRecordCount,
        log.InsertedRows,
        log.UpdatedRows,
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
    INNER JOIN src_nutanix.VirtualMachine AS vm
        ON item.SourceProvider = N''nutanix''
       AND vm.vm_uuid = item.VmUuid
    UNION ALL
    SELECT
        log.BatchId,
        log.BatchScope,
        log.Status,
        log.BatchStartedAt,
        log.BatchFinishedAt,
        log.RawRecordCount,
        log.ProcessedRecordCount,
        log.InsertedRows,
        log.UpdatedRows,
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
    INNER JOIN src_vmware.VirtualMachine AS vm
        ON item.SourceProvider = N''vmware''
       AND vm.vm_uuid = item.VmUuid
    ');
GO
