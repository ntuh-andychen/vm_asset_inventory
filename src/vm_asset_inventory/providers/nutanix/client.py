from __future__ import annotations

import time
import requests
from requests.auth import HTTPBasicAuth
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class NutanixClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        ca_bundle: str = "",
        timeout: int = 30,
        api_limit: int = 500,
        request_delay: float = 0.5,
        proxies: dict[str, str] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_limit = min(api_limit, 500)
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
        verify_value: bool | str = verify_ssl
        if verify_ssl and ca_bundle:
            verify_value = ca_bundle
        self.session.verify = verify_value
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        if proxies:
            self.session.proxies.update(proxies)

    @property
    def api_base(self) -> str:
        return f"{self.base_url}/api/nutanix/v3"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError)),
    )
    def _request(self, method: str, endpoint: str, data: dict | None = None) -> dict:
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        resp = self.session.request(method=method, url=url, json=data, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def fetch_all_vms(self) -> list[dict]:
        out: list[dict] = []
        offset = 0
        total_matches = None

        while True:
            payload = {"kind": "vm", "offset": offset, "length": self.api_limit}
            res = self._request("POST", "/vms/list", data=payload)
            entities = res.get("entities", [])
            meta = res.get("metadata", {})
            if total_matches is None:
                total_matches = int(meta.get("total_matches", 0))
            if not entities:
                break
            out.extend(entities)
            if offset + self.api_limit >= total_matches:
                break
            offset += self.api_limit
            if self.request_delay > 0:
                time.sleep(self.request_delay)

        return out

    def test_connection(self) -> None:
        # Keep probe request small; success means TLS/auth/API route are usable.
        payload = {"kind": "vm", "offset": 0, "length": 1}
        self._request("POST", "/vms/list", data=payload)

    def close(self) -> None:
        self.session.close()
