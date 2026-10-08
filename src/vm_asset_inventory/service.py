from __future__ import annotations

from vm_asset_inventory.models import VMAssetRecord
from vm_asset_inventory.settings import AppConfig


def supported_providers() -> list[str]:
    return ["nutanix", "vmware"]


def _validate_provider(provider: str) -> str:
    name = (provider or "all").strip().lower()
    if name == "all":
        return name
    if name not in supported_providers():
        supported = ", ".join(supported_providers())
        raise ValueError(f"Unsupported provider: {provider}. Supported providers: all, {supported}")
    return name


def test_connections(config: AppConfig, provider: str = "all") -> list[dict[str, str | bool]]:
    provider_lower = _validate_provider(provider)
    results: list[dict[str, str | bool]] = []

    if provider_lower in {"all", "nutanix"}:
        from vm_asset_inventory.providers.nutanix import test_nutanix_connections
        for item in test_nutanix_connections(config.nutanix, proxy_config=config.proxy):
            results.append(
                {
                    "provider": item.provider,
                    "endpoint": item.endpoint,
                    "success": item.success,
                    "message": item.message,
                }
            )

    if provider_lower in {"all", "vmware"}:
        from vm_asset_inventory.providers.vmware import test_vmware_connections
        for item in test_vmware_connections(config.vmware):
            results.append(
                {
                    "provider": item.provider,
                    "endpoint": item.endpoint,
                    "success": item.success,
                    "message": item.message,
                }
            )

    return results


def collect_assets(config: AppConfig, provider: str = "all") -> list[VMAssetRecord]:
    provider_lower = _validate_provider(provider)
    records: list[VMAssetRecord] = []

    if provider_lower in {"all", "nutanix"}:
        from vm_asset_inventory.providers.nutanix import collect_nutanix
        records.extend(collect_nutanix(config.nutanix, proxy_config=config.proxy))

    if provider_lower in {"all", "vmware"}:
        from vm_asset_inventory.providers.vmware import collect_vmware
        records.extend(collect_vmware(config.vmware))

    return records
