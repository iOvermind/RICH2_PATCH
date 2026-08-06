# 大富翁2 Patch 開發者文件

> 這份文件給**要修改這個專案的人**。使用說明請看 [README.md](README.md)。
> 文件與發佈規範見 [docs/rules/](docs/rules/)。

---

## 1. 技術棧與系統需求

| 項目 | 版本 | 用途 |
| :--- | :--- | :--- |
| Python | 3.10 以上（實測 3.14） | 主程式 |
| tkinter | 隨 Python 內附 | 使用者介面 |
| PyInstaller | 6.0 以上 | 打包成單一 EXE |
| Windows SDK（signtool） | 任意版本 | 數位簽章，選用 |

**執行期不需要任何第三方套件**——只用標準函式庫 `tkinter` / `os` / `sys` / `shutil` / `re`。`requirements.txt` 裡的 PyInstaller 僅供打包。

**作業系統限制**：產物僅供 Windows。建置可在 Windows 進行，也可在 Linux/WSL 透過 Wine 執行（見 §7）。

---

## 2. 環境建置

1. 取得原始碼
   ```bash
   git clone git@github.com:iOvermind/RICH2_PATCH.git
   ```

2. 確認 Python 可用
   ```powershell
   python --version
   ```
   應顯示 3.10 以上版本。

3. 安裝打包相依套件（只有要打包時才需要）
   ```powershell
   python -m pip install -r requirements.txt
   ```

4. 準備一份測試用的遊戲資料夾
   需要一份《大富翁2》的 `RUN.EXE`。**遊戲檔案不進版控**（見 §9.1），請自行放在庫外或已被忽略的目錄。

---

## 3. 日常開發

**直接執行**

```powershell
python main.py
```

視窗會開起來，行為與打包後完全相同。開發時不需要每次都打包。

**修改後如何反映**：重新執行 `python main.py` 即可，沒有熱更新。

**除錯**：`emit_log()` 同時寫到終端機與 UI 日誌區。從終端機啟動就能看到完整輸出，格式為 `[狀態][STEP n/total] 訊息`。狀態字串有 `INFO` / `WARN` / `ERROR` / `SUCCESS` / `FATAL` / `DONE`，Rich Patch Series 兩支程式共用同一套。

---

## 4. 目錄結構

```text
RICH2_PATCH/
├─ main.py                  全部的程式碼：patch 邏輯 + tkinter 介面
├─ rich2_patch.spec         PyInstaller 設定，含瘦身用的排除清單
├─ file_version_info.txt    EXE 的版本資源（版本號在這裡）
├─ requirements.txt         打包相依套件
├─ build.ps1                Windows 打包腳本（建議用這支）
├─ build.bat                Windows 打包腳本（雙擊版）
├─ build.sh                 Linux/WSL 打包腳本（透過 Wine）
├─ icon.png / icon.ico      視窗圖示與 EXE 圖示
├─ github.bat / github.sh   推送輔助腳本
└─ docs/rules/              文件與發佈規範（正典在 DEV_TEMPLATE）
```

`main.py` 內部分為四段，以註解分隔：共用工具（`backup_file` / `find_target` / `patch_binary`）、核心處理（`patch_exe`）、主幹邏輯（`run_patch`）、介面（`main`）。

---

## 5. 架構與關鍵設計決策

### 模組職責

單檔程式，但介面與邏輯是分離的：

| 部分 | 職責 |
| :--- | :--- |
| `patch_*` 系列函式 | 實際的二進位修改，完全不碰 UI |
| `emit_log()` | 唯一的輸出管道，透過回呼把訊息送給 UI |
| `run_patch()` | 主幹流程，以回呼 `on_complete` / `on_error` 回報結果 |
| `main()` | 只負責 tkinter 介面與事件綁定 |

### 關鍵決策

#### 介面與邏輯以回呼解耦

- **決定**：patch 邏輯不直接呼叫任何 tkinter API，一律透過 `set_callbacks()` 注入的 `log_cb` / `prog_cb` 回報。
- **理由**：同一套邏輯要能在無介面的環境下執行與驗證；也讓 Rich Patch Series 兩支程式的日誌格式保持一致。
- **代價**：多一層間接，加新訊息時要記得帶 `step` 才會推進進度條。

#### 特徵碼比對只替換第一次出現

- **決定**：`patch_binary()` 對非 `.MKF` 檔案只替換第一個符合的位置（`replace(..., 1)`）。
- **理由**：EXE 內的特徵碼是特定指令位置，全域替換可能誤傷其他剛好相同的位元組序列。
- **代價**：若同一段修改真的需要改多處，必須拆成多條特徵碼。

#### 備份不覆蓋

- **決定**：`backup_file()` 只在 `.bak` 不存在時建立備份。
- **理由**：使用者重複執行是常態。若每次都覆蓋備份，第二次執行後就再也回不到原版。
- **代價**：使用者若手動改壞了 `.bak`，程式不會察覺。

---

## 6. 測試

**目前沒有自動化測試。** 驗證靠手動比對。

建議的驗證流程：

1. 準備一份未修改的 `RUN.EXE`，記下雜湊值：
   ```powershell
   Get-FileHash .\RUN.EXE -Algorithm SHA256
   ```
2. 執行 `python main.py`，選到該資料夾並按開始。
3. 確認日誌四條特徵碼全部顯示「成功」（Steam 典藏版會命中光碟版那兩條，磁片版那兩條顯示跳過，這是正常的）。
4. 確認產生了 `RUN.EXE.bak`，且其雜湊值等於步驟 1 的原始值。
5. 再執行一次，確認 `.bak` 沒有被覆蓋、日誌顯示「找不到特徵碼或已修改」。
6. 進遊戲開一張多人地圖，確認可以單人開局。

---

## 7. 建置與產物

**Windows**

```powershell
.\build.ps1                # 打包
.\build.ps1 -Sign          # 打包並簽章
.\build.ps1 -SkipDeps      # 跳過套件檢查，較快
```

也可以雙擊 `build.bat`（功能相同，但一定會嘗試簽章）。

**Linux / WSL**

```bash
./build.sh                 # 透過 Wine 呼叫 Windows 版 Python
```

簽章改用原生 `osslsigncode`（`sudo apt install osslsigncode`），不走 Wine + signtool。

**產物**

| 產物 | 用途 |
| :--- | :--- |
| `dist/rich2_patch.exe` | 單一執行檔，免安裝。目前唯一的發佈形式。 |

打包**一律走 `rich2_patch.spec`**，不要直接下 `pyinstaller main.py`——`.spec` 裡的模組排除清單與 Tcl/Tk 資源裁切才是體積控制的關鍵（見 §10）。腳本最後會印出成品體積，盯著別讓它肥起來。

> **已知落差**：建置腳本目前輸出 `rich2_patch.exe`，尚未符合
> [docs/rules/RELEASE_RULES.md](docs/rules/RELEASE_RULES.md) §2.1 要求的
> `[RICH2_PATCH][v1.0.0][Portable].exe` 格式。發佈前必須改名，或調整建置腳本。

### 版本號

**單一來源**：`file_version_info.txt`

| 位置 | 欄位 | 方式 |
| :--- | :--- | :--- |
| `file_version_info.txt` | `filevers` / `prodvers` | 手動（單一來源，四元組如 `(1, 0, 0, 0)`） |
| `file_version_info.txt` | `FileVersion` / `ProductVersion` | 手動（字串如 `1.0.0`，須與上者一致） |
| EXE 版本資源 | — | 自動（PyInstaller 由 `.spec` 的 `version=` 讀入） |

發佈前依 [docs/rules/VERSION_RULES.md](docs/rules/VERSION_RULES.md) §7 逐項核對。

---

## 8. 分支、commit 與 PR 慣例

- **主分支**：`main`
- **開分支**：從 `main` 開，功能用 `feat/<描述>`、修正用 `fix/<描述>`。
- **commit 訊息**：首行為繁中祈使句摘要，必要時空一行後補理由。

### 舊實作的保留

目前無。

本專案規劃遷移到 Rust + Tauri（見 [TAURI_MIGRATION.md](TAURI_MIGRATION.md)）。屆時 Python 版**必須**依 `docs/rules/DEVELOPER_RULES.md` §4.3 以分支保留、不得直接刪除；主分支走 Tauri 版。Python 版同時是驗證新實作正確性的基準，須在比對通過後才解除保留。

---

## 9. 安全與敏感資料

### 9.1 機密不進版控

| 項目 | 排除方式 | 本機該放哪 |
| :--- | :--- | :--- |
| 簽章憑證 `Overmind.pfx` | `.gitignore` 的 `*.pfx` | 專案根目錄，由建置腳本自動產生 |
| 遊戲原始檔（`*.EXE` / `*.MKF` / `*.PAT` / `*.bak`…） | `.gitignore` 逐項排除 | 庫外，或 `original/` / `dist/` 等已忽略的目錄 |

⚠ **憑證密碼 `overmind` 以明文寫在 `build.ps1`、`build.bat`、`build.sh` 中。** 這是刻意的權衡：該憑證為自簽、僅用於讓 EXE 帶上發行者名稱，本身不具信任價值，密碼公開不造成額外風險。**因此這張憑證不得用於任何其他用途**；若日後改用有實際信任價值的憑證，密碼必須改由環境變數或憑證存放區提供。

**遊戲原始檔不進版控**的理由是版權，不是體積——這點請維持。

### 9.2 權限最小化

| 要求的權限 | 為什麼需要 |
| :--- | :--- |
| 讀寫使用者選定資料夾內的檔案 | patch 的本質就是改寫遊戲的 `RUN.EXE` |

**刻意不要的權限**：程式不連網、不讀寫使用者選定目錄以外的位置、不寫登錄檔、不需要管理員權限。`.spec` 的排除清單裡明確排掉了 `socket`、`ssl`、`urllib`、`http`——這同時是瘦身也是保證。

### 9.3 依賴來源與鎖檔

- 執行期**零第三方相依**，因此沒有鎖檔。
- 打包相依只有 PyInstaller，來源為 PyPI，版本下限寫在 `requirements.txt`。
- 新增任何執行期相依前請三思：目前的「零相依」是這支工具能單檔散佈的前提。

### 9.4 破壞性操作的保護

| 操作 | 影響的資料 | 可回復機制 |
| :--- | :--- | :--- |
| 改寫 `RUN.EXE` | 使用者的遊戲主程式 | 先複製為 `RUN.EXE.bak`；**若 `.bak` 已存在則不覆蓋**，確保永遠保留最原始的版本。還原方式為把 `.bak` 改名回原檔名。 |

修改任何會寫入使用者檔案的程式碼時，都必須維持這個「備份優先、不覆蓋既有備份」的原則。

---

## 10. 已知陷阱

#### 直接用 `pyinstaller main.py` 打包，EXE 會肥好幾 MB

- **症狀**：打包成功，但產出的 EXE 明顯大於預期（10 MB 以上）。
- **原因**：`.spec` 裡的 `EXCLUDES`（排除 numpy、PyQt、asyncio 等）與 Tcl/Tk 資源裁切（`TRIM_DIRS`、`KEEP_ENCODINGS`）只有走 `.spec` 才會生效；直接指定 `main.py` 會用預設設定重新產生一份 spec。
- **處置**：一律 `python -m PyInstaller --clean --noconfirm rich2_patch.spec`，或直接用 `build.ps1`。

#### 砍掉 Tcl 的 encoding 後程式啟動就閃退

- **症狀**：打包後的 EXE 雙擊沒反應或瞬間關閉，從終端機執行可看到 Tcl 初始化相關錯誤。
- **原因**：`.spec` 的 `KEEP_ENCODINGS` 只保留了必要的編碼檔。若把 `ascii.enc`、`utf-8.enc`、`unicode.enc`、`cp950.enc` 之類移除，Tcl 啟動或繁中環境就會失敗。
- **處置**：調整 `KEEP_ENCODINGS` 後**必須**實際執行打包出來的 EXE 驗證，不能只看打包有沒有成功。

#### Steam 典藏版只會命中一半的特徵碼

- **症狀**：日誌顯示四條特徵碼中兩條「成功」、兩條「跳過 (找不到特徵碼或已修改)」。
- **原因**：磁片版與光碟版的偏移位址不同，程式兩套都試。任一版本本來就只會命中對應的那兩條。
- **處置**：這是正常行為，不是錯誤。判斷成功與否要看**是否有任何一條成功**，不是看是否四條全中。

#### 在 Linux 上用 Wine 打包，簽章步驟會卡住

- **症狀**：`build.sh` 執行到簽章時無回應或報錯。
- **原因**：Wine 底下跑 Windows 版 `signtool.exe` 極不穩定。
- **處置**：`build.sh` 已改用 Linux 原生的 `osslsigncode`。沒安裝的話腳本會提示並跳過簽章，產物仍然可用。

---

## 相關文件

- 使用說明：[README.md](README.md)
- 變更紀錄：[CHANGELOG.md](CHANGELOG.md)
- 遷移計畫：[TAURI_MIGRATION.md](TAURI_MIGRATION.md)
- 文件與發佈規範：[docs/rules/](docs/rules/)
