from __future__ import annotations

import atexit
import ssl
from typing import Any

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim


class VMwareClient:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 443,
        verify_ssl: bool = False,
        ca_bundle: str = "",
    ):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.verify_ssl = verify_ssl
        self.ca_bundle = ca_bundle
        self._si: Any = None
        self._content: Any = None

    def _ssl_context(self) -> ssl.SSLContext:
        if self.verify_ssl:
            ctx = ssl.create_default_context()
            if self.ca_bundle:
                ctx.load_verify_locations(cafile=self.ca_bundle)
            return ctx
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def connect(self) -> None:
        self._si = SmartConnect(
            host=self.host,
            user=self.username,
            pwd=self.password,
            port=self.port,
            sslContext=self._ssl_context(),
        )
        self._content = self._si.RetrieveContent()
        atexit.register(Disconnect, self._si)

    def disconnect(self) -> None:
        if self._si:
            Disconnect(self._si)
            self._si = None
            self._content = None

    def list_vms(self) -> list[Any]:
        if not self._content:
            raise RuntimeError("VMware client is not connected")
        container = self._content.viewManager.CreateContainerView(
            self._content.rootFolder,
            [vim.VirtualMachine],
            True,
        )
        vms = list(container.view)
        container.Destroy()
        return vms
