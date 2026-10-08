from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import yaml


@dataclass
class GeneralConfig:
    output_dir: str = "output"
    timeout_seconds: int = 30


class ConfigError(Exception):
    pass


@dataclass
class ConfigModules:
    credentials_file: str = "config/credentials.yaml"
    sources_file: str = "config/sources.yaml"
    source_credentials_file: str = ""
    proxy_file: str = "config/proxy.yaml"


@dataclass
class ProxyProfileConfig:
    http_proxy: str = ""
    https_proxy: str = ""
    no_proxy: str = ""


@dataclass
class ProxyConfig:
    enabled: bool = False
    default_profile: str = ""
    profiles: dict[str, ProxyProfileConfig] = field(default_factory=dict)
    feature_bindings: dict[str, str] = field(default_factory=dict)

    def resolve_profile_name(self, feature: str) -> str:
        return self.feature_bindings.get(feature, self.default_profile)

    def resolve_requests_proxies(self, feature: str) -> dict[str, str]:
        if not self.enabled:
            return {}

        profile_name = self.resolve_profile_name(feature)
        if not profile_name:
            return {}

        profile = self.profiles.get(profile_name)
        if not profile:
            raise ConfigError(f"Proxy profile not found for feature {feature}: {profile_name}")

        proxies: dict[str, str] = {}
        if profile.http_proxy:
            proxies["http"] = profile.http_proxy
        if profile.https_proxy:
            proxies["https"] = profile.https_proxy
        return proxies

    def resolve_no_proxy(self, feature: str) -> str:
        if not self.enabled:
            return ""

        profile_name = self.resolve_profile_name(feature)
        if not profile_name:
            return ""

        profile = self.profiles.get(profile_name)
        if not profile:
            raise ConfigError(f"Proxy profile not found for feature {feature}: {profile_name}")
        return profile.no_proxy


@dataclass
class CredentialConfig:
    id: str
    username: str
    password: str = ""
    password_env: str = ""

    def resolved_password(self) -> str:
        if self.password_env:
            return os.getenv(self.password_env, "")
        return self.password


@dataclass
class NutanixEndpointConfig:
    name: str
    base_url: str
    username: str = ""
    password: str = ""
    credential_id: str = ""
    proxy_feature: str = "nutanix_api"
    verify_ssl: bool = False
    ca_bundle: str = ""
    api_limit: int = 500
    request_delay: float = 0.5


@dataclass
class VMwareEndpointConfig:
    name: str
    host: str
    username: str = ""
    password: str = ""
    credential_id: str = ""
    proxy_feature: str = "vmware_api"
    port: int = 443
    verify_ssl: bool = False
    ca_bundle: str = ""
    host_type: str = "vcenter"


@dataclass
class ReportFilterConfig:
    providers: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    powerstates: list[str] = field(default_factory=list)
    vmname_contains: str = ""
    cluster_contains: str = ""
    min_ram_mib: int = 0
    min_disk_gb: float = 0.0
    require_ip: bool = False


@dataclass
class ReportConfig:
    output_prefix: str = "vm_asset_inventory_report"
    filters: ReportFilterConfig = field(default_factory=ReportFilterConfig)
    summary_group_by: list[str] = field(
        default_factory=lambda: ["source_provider", "source_platform", "powerstate"]
    )


@dataclass
class SqlServerTargetConfig:
    enabled: bool = False
    server: str = ""
    local_server: str = ""
    connection_mode: str = "auto"
    database: str = "ExampleInventory"
    driver: str = "ODBC Driver 18 for SQL Server"
    authentication: str = "integrated"
    username: str = ""
    password_env: str = ""
    trust_server_certificate: bool = False
    table_map: dict[str, str] = field(
        default_factory=lambda: {
            "nutanix": "src_nutanix.VirtualMachine",
            "vmware": "src_vmware.VirtualMachine",
        }
    )

    def resolve_server(self) -> str:
        mode = str(self.connection_mode or "auto").strip().lower()
        remote_server = str(self.server or "").strip()
        local_server = str(self.local_server or "").strip()

        if mode == "remote":
            return remote_server
        if mode == "local":
            return local_server or remote_server
        if remote_server:
            return remote_server
        return local_server

    def resolve_connection_label(self) -> str:
        mode = str(self.connection_mode or "auto").strip().lower()
        if mode in {"remote", "local"}:
            return mode
        if self.server:
            return "remote"
        if self.local_server:
            return "local"
        return "unset"


@dataclass
class OutputConfig:
    mode: str = "auto"
    debug_files: bool = False
    sqlserver: SqlServerTargetConfig = field(default_factory=SqlServerTargetConfig)

    def resolve_targets(self) -> list[str]:
        mode = str(self.mode or "auto").strip().lower()
        targets: list[str] = []

        if mode == "auto":
            targets.append("database" if self.sqlserver.enabled else "file")
        elif mode == "database":
            if not self.sqlserver.enabled:
                raise ConfigError("output.mode is 'database' but output.sqlserver.enabled is false")
            targets.append("database")
        elif mode == "file":
            targets.append("file")
        elif mode == "both":
            if self.sqlserver.enabled:
                targets.append("database")
            targets.append("file")
        else:
            raise ConfigError(f"Unsupported output mode: {self.mode}")

        if self.debug_files and "file" not in targets:
            targets.append("file")

        return targets


@dataclass
class AppConfig:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    modules: ConfigModules = field(default_factory=ConfigModules)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    nutanix: list[NutanixEndpointConfig] = field(default_factory=list)
    vmware: list[VMwareEndpointConfig] = field(default_factory=list)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_path(base_file: Path, child_path: str) -> Path:
    child = Path(child_path)
    if child.is_absolute():
        return child

    # Prefer explicit path from current working directory when it exists.
    if child.exists():
        return child.resolve()

    # Fall back to path relative to config file location.
    candidate = (base_file.parent / child).resolve()
    return candidate


def _resolve_optional_path(base_file: Path, child_path: str) -> str:
    text = str(child_path or "").strip()
    if not text:
        return ""
    return str(_resolve_path(base_file, text))


def _build_credential_map(items: list[dict]) -> dict[str, CredentialConfig]:
    out: dict[str, CredentialConfig] = {}
    for item in items:
        cfg = CredentialConfig(**item)
        if cfg.id in out:
            raise ConfigError(f"Duplicate credential id: {cfg.id}")
        out[cfg.id] = cfg
    return out


def _build_proxy_config(data: dict) -> ProxyConfig:
    proxy = ProxyConfig(
        enabled=bool(data.get("enabled", False)),
        default_profile=str(data.get("default_profile", "")),
        feature_bindings=dict(data.get("feature_bindings") or {}),
    )

    profiles = data.get("profiles") or {}
    for profile_name, profile_data in profiles.items():
        proxy.profiles[str(profile_name)] = ProxyProfileConfig(**(profile_data or {}))

    return proxy


def _build_report_config(data: dict) -> ReportConfig:
    filters_data = data.get("filters") or {}
    filters = ReportFilterConfig(
        providers=[str(x).lower() for x in (filters_data.get("providers") or [])],
        platforms=[str(x) for x in (filters_data.get("platforms") or [])],
        powerstates=[str(x).lower() for x in (filters_data.get("powerstates") or [])],
        vmname_contains=str(filters_data.get("vmname_contains") or ""),
        cluster_contains=str(filters_data.get("cluster_contains") or ""),
        min_ram_mib=int(filters_data.get("min_ram_mib") or 0),
        min_disk_gb=float(filters_data.get("min_disk_gb") or 0.0),
        require_ip=bool(filters_data.get("require_ip", False)),
    )

    summary_group_by = [str(x) for x in (data.get("summary_group_by") or [])]
    if not summary_group_by:
        summary_group_by = ["source_provider", "source_platform", "powerstate"]

    return ReportConfig(
        output_prefix=str(data.get("output_prefix") or "vm_asset_inventory_report"),
        filters=filters,
        summary_group_by=summary_group_by,
    )


def _build_output_config(data: dict) -> OutputConfig:
    sqlserver_data = data.get("sqlserver") or {}
    table_map = dict(sqlserver_data.get("table_map") or {})
    if not table_map:
        table_map = {
            "nutanix": "src_nutanix.VirtualMachine",
            "vmware": "src_vmware.VirtualMachine",
        }

    sqlserver = SqlServerTargetConfig(
        enabled=bool(sqlserver_data.get("enabled", False)),
        server=str(sqlserver_data.get("server") or ""),
        local_server=str(sqlserver_data.get("local_server") or ""),
        connection_mode=str(sqlserver_data.get("connection_mode") or "auto"),
        database=str(sqlserver_data.get("database") or "ExampleInventory"),
        driver=str(sqlserver_data.get("driver") or "ODBC Driver 18 for SQL Server"),
        authentication=str(sqlserver_data.get("authentication") or "integrated").lower(),
        username=str(sqlserver_data.get("username") or ""),
        password_env=str(sqlserver_data.get("password_env") or ""),
        trust_server_certificate=bool(sqlserver_data.get("trust_server_certificate", False)),
        table_map={str(key).lower(): str(value) for key, value in table_map.items()},
    )

    return OutputConfig(
        mode=str(data.get("mode") or "auto"),
        debug_files=bool(data.get("debug_files", False)),
        sqlserver=sqlserver,
    )


def _apply_credential(
    provider_name: str,
    endpoint_name: str,
    endpoint: dict,
    credential_map: dict[str, CredentialConfig],
) -> dict:
    endpoint_out = dict(endpoint)

    inline_password = str(endpoint_out.get("password", "") or "")
    inline_password_env = str(endpoint_out.get("password_env", "") or "")
    if not inline_password and inline_password_env:
        endpoint_out["password"] = os.getenv(inline_password_env, "")

    if endpoint_out.get("username") and endpoint_out.get("password"):
        endpoint_out.pop("password_env", None)
        return endpoint_out

    cred_id = endpoint_out.get("credential_id", "")
    if not cred_id:
        raise ConfigError(
            f"Missing credential_id or inline username/password for {provider_name} endpoint: {endpoint_name}"
        )

    cred = credential_map.get(cred_id)
    if not cred:
        raise ConfigError(
            f"Credential id not found for {provider_name} endpoint {endpoint_name}: {cred_id}"
        )

    resolved_password = cred.resolved_password()
    if not resolved_password:
        raise ConfigError(
            f"Resolved password is empty for credential id: {cred_id} (provider {provider_name}, endpoint {endpoint_name})"
        )

    endpoint_out["username"] = cred.username
    endpoint_out["password"] = resolved_password
    endpoint_out.pop("password_env", None)
    return endpoint_out


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path)
    data = _load_yaml(path)
    source_origin_path = path

    general = GeneralConfig(**(data.get("general") or {}))
    modules = ConfigModules(**(data.get("modules") or {}))

    credentials_data = data.get("credentials") or {}
    sources_data = data.get("sources") or {}
    proxy_data = data.get("proxy") or {}
    report_data = data.get("report") or {}
    output_data = data.get("output") or {}

    # Preferred modular mode: load from module files if configured.
    if data.get("modules"):
        credentials_path = _resolve_path(path, modules.credentials_file)
        sources_path = _resolve_path(path, modules.sources_file)
        proxy_path = _resolve_path(path, modules.proxy_file)

        # New mode: one file contains both credentials and sources.
        if modules.source_credentials_file:
            merged_path = _resolve_path(path, modules.source_credentials_file)
            merged_data = _load_yaml(merged_path)
            credentials_data = merged_data.get("credentials") or {}
            sources_data = merged_data.get("sources") or {}
            report_data = merged_data.get("report") or report_data
            output_data = merged_data.get("output") or output_data
            source_origin_path = merged_path
        # Compatibility mode: credentials_file and sources_file can point to same file.
        elif credentials_path == sources_path:
            merged_data = _load_yaml(credentials_path)
            if "credentials" in merged_data or "sources" in merged_data:
                credentials_data = merged_data.get("credentials") or {}
                sources_data = merged_data.get("sources") or {}
                report_data = merged_data.get("report") or report_data
                output_data = merged_data.get("output") or output_data
                source_origin_path = credentials_path
            else:
                # Treat as sources-only file. Endpoints can use inline username/password/password_env.
                credentials_data = {}
                sources_data = merged_data
                source_origin_path = sources_path
        else:
            credentials_data = _load_yaml(credentials_path)
            sources_data = _load_yaml(sources_path)
            source_origin_path = sources_path

        proxy_data = _load_yaml(proxy_path)

    # Backward compatibility: allow old inline format.
    if not sources_data:
        sources_data = {
            "nutanix": data.get("nutanix") or [],
            "vmware": data.get("vmware") or [],
        }

    nutanix_credentials = _build_credential_map(credentials_data.get("nutanix") or [])
    vmware_credentials = _build_credential_map(credentials_data.get("vmware") or [])

    nutanix_sources = sources_data.get("nutanix") or []
    vmware_sources = sources_data.get("vmware") or []

    nutanix: list[NutanixEndpointConfig] = []
    for item in nutanix_sources:
        name = str(item.get("name", ""))
        resolved = _apply_credential("nutanix", name, item, nutanix_credentials)
        resolved["ca_bundle"] = _resolve_optional_path(source_origin_path, resolved.get("ca_bundle", ""))
        nutanix.append(NutanixEndpointConfig(**resolved))

    vmware: list[VMwareEndpointConfig] = []
    for item in vmware_sources:
        name = str(item.get("name", ""))
        resolved = _apply_credential("vmware", name, item, vmware_credentials)
        resolved["ca_bundle"] = _resolve_optional_path(source_origin_path, resolved.get("ca_bundle", ""))
        vmware.append(VMwareEndpointConfig(**resolved))

    proxy = _build_proxy_config(proxy_data)
    output = _build_output_config(output_data)
    report = _build_report_config(report_data)

    return AppConfig(
        general=general,
        modules=modules,
        proxy=proxy,
        output=output,
        report=report,
        nutanix=nutanix,
        vmware=vmware,
    )
