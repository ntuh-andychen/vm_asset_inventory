# Python + uv Proxy Download and Offline Installation Guide

This guide follows C:/Projects/Python/specification/constitution.md principles:
- External access must go through proxy.
- Proxy values must be injected by environment variables.
- Runtime should be offline-capable after dependency preparation.

## 1) Rules summary
- Do not hardcode proxy address inside application source code.
- Use environment variables:
  - HTTP_PROXY
  - HTTPS_PROXY
  - NO_PROXY
- Separate "download phase" and "runtime phase".
- Keep lock-based dependency restore:
  - uv.lock in version control
  - uv sync --frozen in build/install flow
- Run offline smoke test before release.

## 2) Connected machine (prepare offline bundle)
Use script:
- scripts/prepare-offline-python-uv.ps1

It will:
- read proxy from ../shared_proxy/proxy.yaml by feature `offline_download` (or override by parameter)
- set proxy from config/parameters to env vars
- download Python embeddable package
- download uv binary
- export requirements from lock context
- prefetch dependencies with `uv sync --frozen`
- copy `uv cache dir` into bundle for offline restore
- output offline bundle folder

## 3) Offline machine (install from bundle)
Use script:
- scripts/install-offline-python-uv.ps1

It will:
- extract Python embeddable
- enable site-packages in python._pth
- ensure uv executable exists locally
- restore dependencies from bundled uv cache using `uv sync --offline`
- run offline validation command

## 4) Example command sequence
On connected machine:
- ./scripts/prepare-offline-python-uv.ps1 -ProxyConfigPath shared_proxy/proxy.yaml -ProxyFeature offline_download -PythonVersion 3.12.10 -BundleDir output/offline_bundle

Optional override:
- ./scripts/prepare-offline-python-uv.ps1 -ProxyUrl http://host132.example.com:3128 -PythonVersion 3.12.10 -BundleDir output/offline_bundle

On offline machine:
- ./scripts/install-offline-python-uv.ps1 -BundleDir output/offline_bundle -InstallDir runtime/python-embed

## 5) Security notes
- Prefer password_env in config/credentials.yaml.
- Do not commit real passwords.
- If audit tools are not fully available, keep pending-scan-report.md as required by specification.
