USE ExampleInventory;
GO

IF COL_LENGTH(N'ops.SyncBatchLog', N'RunnerHost') IS NULL
    ALTER TABLE ops.SyncBatchLog ADD RunnerHost nvarchar(128) NULL;
GO

IF COL_LENGTH(N'ops.SyncBatchLog', N'RunnerUser') IS NULL
    ALTER TABLE ops.SyncBatchLog ADD RunnerUser nvarchar(128) NULL;
GO

IF COL_LENGTH(N'ops.SyncBatchLog', N'DeletedRows') IS NULL
    ALTER TABLE ops.SyncBatchLog ADD DeletedRows int NOT NULL CONSTRAINT DF_ops_SyncBatchLog_DeletedRows DEFAULT (0);
GO

IF COL_LENGTH(N'ops.SyncBatchLog', N'DurationSeconds') IS NULL
    ALTER TABLE ops.SyncBatchLog ADD DurationSeconds int NULL;
GO

IF OBJECT_ID(N'ops.vwSyncBatchCurrentVmRelation', N'V') IS NOT NULL
    DROP VIEW ops.vwSyncBatchCurrentVmRelation;
GO

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
    ON item.SourceProvider = N'nutanix'
   AND vm.vm_uuid = item.VmUuid
WHERE item.SourceProvider = N'nutanix'
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
    ON item.SourceProvider = N'vmware'
    AND vm.vm_uuid = item.VmUuid
WHERE item.SourceProvider = N'vmware';
GO
