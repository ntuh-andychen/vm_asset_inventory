# GitHub 版本部署設定

此版本不含正式設定、憑證、個資、業務 Excel、日誌或資料庫備份。
範本中的 example、192.0.2.x、零值識別碼與 REPLACE_ME 必須按新環境替換。

## 本機設定

先複製範本；若目標設定已存在，保留原檔，不要覆寫。

```powershell
if (-not (Test-Path -LiteralPath 'config/config.yaml')) { Copy-Item -LiteralPath 'config/config.template.yaml' -Destination 'config/config.yaml' }
if (-not (Test-Path -LiteralPath 'config/proxy.yaml')) { Copy-Item -LiteralPath 'config/proxy.template.yaml' -Destination 'config/proxy.yaml' }
if (-not (Test-Path -LiteralPath 'config/sources.yaml')) { Copy-Item -LiteralPath 'config/sources.template.yaml' -Destination 'config/sources.yaml' }
if (-not (Test-Path -LiteralPath 'config/source_credentials.yaml')) { Copy-Item -LiteralPath 'config/source_credentials.template.yaml' -Destination 'config/source_credentials.yaml' }
```

依序設定服務 URL／主機、資料庫、租用戶與用戶端 ID、帳密／API 金鑰；只填写實際使用的欄位。
若設定提供 *_env 欄位，請依程式既有支援使用本機環境變數保存秘密。範本不會自動展開任意 ${VAR}。
不要執行仍含 REPLACE_ME 的設定，也不要將填入後的設定加入 Git。

## 環境與依賴

Python 專案請依 pyproject.toml 或 requirements.txt 建立獨立虛擬環境並安裝相依套件。
需要 SQL Server 的專案請安裝其指定 ODBC Driver，依 README 與 database／sql 文件初始化新環境。
同步、匯入與初始化指令可能存取外部 API 或寫入資料庫；此次發布只進行離線檢查。

此專案引用同層共用專案，請將下列 repo clone 至同一父目錄，並完成其本機設定：
- `shared_proxy`
