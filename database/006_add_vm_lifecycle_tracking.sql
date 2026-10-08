USE ExampleInventory;
GO
DECLARE @Schema sysname;
DECLARE schemas CURSOR LOCAL FAST_FORWARD FOR SELECT name FROM sys.schemas WHERE name IN(N'src_nutanix',N'src_vmware');
OPEN schemas;FETCH NEXT FROM schemas INTO @Schema;
WHILE @@FETCH_STATUS=0
BEGIN
 DECLARE @Sql nvarchar(max)=N'
 IF OBJECT_ID(N'''+QUOTENAME(@Schema)+N'.VirtualMachineLifecycle'',N''U'') IS NULL
 BEGIN
  CREATE TABLE '+QUOTENAME(@Schema)+N'.VirtualMachineLifecycle(
   VirtualMachineLifecycleId bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_'+REPLACE(@Schema,N'_',N'')+N'_VMLifecycle PRIMARY KEY,
   vm_uuid nvarchar(100) NOT NULL,VmCreatedAt datetime2(0) NULL,AssetDescription nvarchar(max) NULL,
   CurrentPowerState nvarchar(20) NOT NULL,PowerStateChangedAt datetime2(0) NOT NULL,
   LastPoweredOffAt datetime2(0) NULL,LastPoweredOnAt datetime2(0) NULL,
   SourceObservedAt datetime2(0) NOT NULL,BatchId nvarchar(50) NOT NULL,
   CreatedAt datetime2(0) NOT NULL DEFAULT(SYSDATETIME()),UpdatedAt datetime2(0) NOT NULL DEFAULT(SYSDATETIME()),
   ValidFrom datetime2(7) GENERATED ALWAYS AS ROW START NOT NULL,ValidTo datetime2(7) GENERATED ALWAYS AS ROW END NOT NULL,
   PERIOD FOR SYSTEM_TIME(ValidFrom,ValidTo),CONSTRAINT UQ_'+REPLACE(@Schema,N'_',N'')+N'_VMLifecycle_UUID UNIQUE(vm_uuid)
  )WITH(SYSTEM_VERSIONING=ON(HISTORY_TABLE='+QUOTENAME(@Schema)+N'.VirtualMachineLifecycleHistory,DATA_CONSISTENCY_CHECK=ON));
 END;
 IF OBJECT_ID(N'''+QUOTENAME(@Schema)+N'.VirtualMachinePowerEvent'',N''U'') IS NULL
 BEGIN
  CREATE TABLE '+QUOTENAME(@Schema)+N'.VirtualMachinePowerEvent(
   VirtualMachinePowerEventId bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_'+REPLACE(@Schema,N'_',N'')+N'_VMPowerEvent PRIMARY KEY,
   vm_uuid nvarchar(100) NOT NULL,PreviousPowerState nvarchar(20) NULL,CurrentPowerState nvarchar(20) NOT NULL,
   EventType varchar(30) NOT NULL,OccurredAt datetime2(0) NOT NULL,SourceObservedAt datetime2(0) NOT NULL,
   BatchId nvarchar(50) NOT NULL,RecordedAt datetime2(0) NOT NULL DEFAULT(SYSDATETIME())
  );
  CREATE INDEX IX_'+REPLACE(@Schema,N'_',N'')+N'_VMPowerEvent_UUID ON '+QUOTENAME(@Schema)+N'.VirtualMachinePowerEvent(vm_uuid,OccurredAt DESC);
 END;';
 EXEC sys.sp_executesql @Sql;
 FETCH NEXT FROM schemas INTO @Schema;
END
CLOSE schemas;DEALLOCATE schemas;
GO
