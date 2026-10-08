# Source Field Inventory (Phase 1)

This document inventories source fields for Nutanix and VMware before database table design.

## Scope
- Only Nutanix and VMware sources.
- Focus on raw asset collection first.
- Database table design is deferred to phase 2.

## Required collection fields
- sock
- vCore
- vTotalCore
- RAM (export as GB)
- vlanname (multi-values separated by `:`)
- ip (multi-values separated by `:`)
- mac (multi-values separated by `;`)
- disk_spec (per-disk segments separated by `;`)
- describ

## Canonical output columns
- vm_uuid
- source_provider
- source_platform
- cluster
- vmname
- powerstate
- sock
- vCore
- vTotalCore
- RAM_GB
- disk_spec
- vlanname
- ip
- mac
- describ
- osversion
- creat_date
- collected_at

## Source mapping summary

### Nutanix
- vmname: `spec.name` or `status.name`
- vm_uuid: `metadata.uuid`
- cluster: `spec.cluster_reference.name` or `status.cluster_reference.name`
- sock: `status.resources.num_sockets` or `spec.resources.num_sockets`
- vCore: `status.resources.num_vcpus_per_socket` or `spec.resources.num_vcpus_per_socket`
- vTotalCore: `status.resources.num_vcpus` (fallback `sock * vCore`)
- RAM: `status.resources.memory_size_mib`
- Disk: sum of `status.resources.disk_list[*].disk_size_mib` converted to GB
- vlanname: `status.resources.nic_list[*].subnet_reference.name`
- vlanid: `status.resources.nic_list[*].subnet_reference.uuid`
- ip: `status.resources.nic_list[*].ip_endpoint_list[*].ip` (IPv4)
- mac: `status.resources.nic_list[*].mac_address`
- disk_spec: disk bus/index + size summary
- describ: `spec.description` or `status.description`

### VMware
- vmname: `vm.config.name`
- vm_uuid: `vm.config.instanceUuid` or `vm.config.uuid`
- cluster: `vm.runtime.host.parent.name`
- host: `vm.runtime.host.name`
- sock: computed from `numCPU / numCoresPerSocket`
- vCore: `vm.config.hardware.numCoresPerSocket`
- vTotalCore: `vm.config.hardware.numCPU`
- RAM: `vm.config.hardware.memoryMB`
- Disk: sum of `VirtualDisk.capacityInKB` converted to GB
- vlanname: network name from NIC backing/network summary
- vlanid: distributed port group key or switch UUID when available
- ip: guest NIC IPs (IPv4)
- mac: NIC MAC addresses
- disk_spec: per-disk label + size + thin/thick
- describ: `vm.config.annotation`

## Design notes for next phase (DB tables)
- Keep source tables separated:
  - src_nutanix.VirtualMachine
  - src_vmware.VirtualMachine
- Keep all raw columns first, avoid premature transformation.
- Add ingestion metadata columns in each source table:
  - BatchId
  - CollectedAt
  - SourcePlatform
  - SourceProvider

## Important
This phase intentionally does not create database tables. It prepares stable, repeatable source inventory output for table design and query planning.

## Field mapping contract
- No cross-field fallback is allowed across semantic domains.
- Each output column must only receive values from its mapped source field set.
- If a mapped source field is unavailable in the provider API response, output must be empty string (not copied from other columns).
- `source_provider` is normalized token output and should remain provider-specific (`nutanix`, `vmware`, future providers).
- Multi-line text fields from source APIs are normalized to single-line output during export to avoid CSV row confusion.
