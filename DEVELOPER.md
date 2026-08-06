# 大富翁2 Patch 開發者文件

> 這份文件給**要修改這個專案的人**。使用說明請看 [README.md](README.md)。
> 文件與發佈規範見 [docs/rules/](docs/rules/)。

> ⚠ **本專案正在遷移中。** `main` 已改為 Rust + Tauri，Python + tkinter 版仍留在庫內
> 當作驗證正確性的基準（oracle），驗收通過後才會移除。詳見
> [TAURI_MIGRATION.md](TAURI_MIGRATION.md) 與 §8。
> **目前對外發佈的仍是 Python 版**，Tauri 版的前端 UI 尚未接上（遷移計畫步驟 3）。

---

## 1. 技術棧與系統需求

### Tauri 版（`main` 的主線）

| 項目 | 版本 | 用途 |
| :--- | :--- | :--- |
| Rust | 1.77 以上（實測 1.97.1） | patch 引擎與桌面外殼 |
| Tauri | 2 | 桌面框架 |
| Node.js | 實測 v25.8.1 | 前端建置 |
| TypeScript | 5.9 | 前端 |
| Vite | 8 | 開發伺服器與打包 |
| Tailwind CSS | 4 | 樣式（建置時產出，不連 CDN） |
| MSVC Build Tools | — | 編譯 Rust，需「使用 C++ 的桌面開發」工作負載 |
| WebView2 Runtime | — | **執行**所需，Windows 10/11 已內建 |

Node 與 Rust 的版本下限未逐一實測，以 Vite 8 與 `Cargo.toml` 的 `rust-version` 為準。

### Python 版（保留中的 oracle）

| 項目 | 版本 | 用途 |
| :--- | :--- | :--- |
| Python | 3.10 以上（實測 3.14） | 基準實作 |
| tkinter | 隨 Python 內附 | 基準實作的介面 |
| PyInstaller | 6.0 以上 | 打包成單一 EXE |

**作業系統限制**：產物僅供 Windows。

---

## 2. 環境建置

1. 取得原始碼
   ```bash
   git clone git@github.com:iOvermind/RICH2_PATCH.git
   ```

2. 安裝前端相依
   ```powershell
   npm ci
   ```
   ⚠ 用 `npm ci` 不要用 `npm install`——前者依鎖檔安裝，結果可重現。本專案的相依很乾淨，
   **不需要** `--legacy-peer-deps`（那是 RICH2_EDITOR 才有的限制）。

3. 安裝 Rust 工具鏈
   ```powershell
   winget install Rustlang.Rustup
   ```
   再從 Visual Studio Installer 安裝「**使用 C++ 的桌面開發**」工作負載。

4. 驗證
   ```powershell
   npm run build              # 前端，數百毫秒
   cd src-tauri; cargo test   # 引擎的單元測試
   ```
   第一次 `cargo test` 要編譯整個 Tauri 相依樹，約 5–6 分鐘（見 §10）。

5. 準備測試用的遊戲資料夾（選用）
   需要一份《大富翁2》的 `RUN.EXE`。**遊戲檔案不進版控**（見 §9.1），沒有的話 oracle
   測試會自動略過（見 §6）。

6. 只要跑 Python 版當基準時，另外安裝
   ```powershell
   python -m pip install -r requirements.txt
   ```

---

## 3. 日常開發

**桌面版**

```powershell
npm run app:dev            # 原生視窗 + Vite HMR
```

**只開前端**

```powershell
npm run dev                # http://localhost:5173，沒有 Tauri API
```

**Python 基準版**

```powershell
python main.py
```

**修改後如何反映**：前端有 HMR；改到 Rust 需要重啟 `app:dev`（Tauri 會自動重編）。

**除錯**：引擎的每一則訊息同時走兩條路——

- `println!` 到終端機，格式為 `[狀態][STEP n/total] 訊息`，**與 Python 版逐字相同**，方便兩版並排對照。
- Tauri 事件 `patch://log`，酬載為 `{ level, message, step, total }`，供前端顯示。

狀態字串為 `INFO` / `WARN` / `ERROR` / `SUCCESS` / `FATAL` / `DONE`，Rich Patch Series 共用同一套。

---

## 4. 目錄結構

```text
RICH2_PATCH/
├─ index.html               視窗外殼
├─ package.json             前端相依與 scripts（版本號的單一來源）
├─ vite.config.ts
├─ tsconfig.json
├─ src/
│  ├─ main.ts               前端進入點：綁事件、收 Rust 送來的日誌與進度
│  └─ style.css             Tailwind 設定與色票，與 RICH2_EDITOR 同一份 @theme
├─ src-tauri/
│  ├─ Cargo.toml            Rust 相依與 release profile
│  ├─ tauri.conf.json       視窗、bundle、identifier
│  ├─ capabilities/         Tauri 權限宣告（見 §9.2）
│  ├─ icons/                由 icon.png 產生的全套圖示
│  ├─ src/
│  │  ├─ main.rs            進入點，只呼叫 lib
│  │  ├─ lib.rs             Tauri 外殼、指令、事件轉送
│  │  └─ patch/
│  │     ├─ mod.rs          共用引擎：backup_file / patch_binary / Reporter
│  │     └─ rich2.rs        RUN.EXE 的 4 條特徵碼與主幹流程
│  └─ tests/oracle.rs       拿真實遊戲檔跑一遍，供與 Python 版比對
├─ main.py                  ← Python 基準版，驗收通過後移除
├─ rich2_patch.spec         ← 同上
├─ file_version_info.txt    ← 同上
├─ build.ps1 / .bat / .sh   ← Python 版的打包腳本，同上
└─ docs/rules/              文件與發佈規範（正典在 DEV_TEMPLATE）
```

---

## 5. 架構與關鍵設計決策

### 模組職責

| 模組 | 職責 | 依賴 |
| :--- | :--- | :--- |
| `patch::mod` | 共用引擎：特徵碼比對、備份、寫檔、摘要格式 | **不依賴 Tauri** |
| `patch::rich2` | 《大富翁2》專屬：4 條特徵碼與主幹流程 | `patch::mod` |
| `lib.rs` | Tauri 外殼：指令、把引擎輸出轉成事件 | 以上兩者 + Tauri |
| `src/main.ts` | 前端：畫面與事件 | Tauri API |

### 關鍵決策

#### patch 引擎放 Rust，不放前端

- **決定**：所有二進位處理在 `src-tauri/src/patch/`，前端只負責畫面。
- **理由**：patcher 沒有瀏覽器版的需求，把引擎留在 Rust 就**不必把檔案系統權限開放給前端**——前端只需要 dialog 來挑資料夾（見 §9.2）。
- **代價**：與 RICH2_EDITOR 相反的分工，兩個專案的架構不能互相套用。那邊邏輯在前端 TypeScript，因為它要同時服務桌面版與瀏覽器版。

#### 引擎以 `Reporter` trait 與 Tauri 解耦

- **決定**：`patch` 模組不引用任何 Tauri 型別，輸出一律走 `Reporter` trait；`lib.rs` 提供 Tauri 實作，測試提供收集用的實作。
- **理由**：**這是能做 oracle 比對的前提**。同一份引擎要能在沒有視窗的情況下跑，才能和 Python 版比對輸出（見 §6）。這也延續了 Python 版「介面與邏輯以回呼解耦」的決策。
- **代價**：多一層間接；加新訊息時要記得帶 `step` 才會推進進度條。

#### 替換範圍由 `ReplaceMode` 決定，而非硬寫

- **決定**：`ReplaceMode::First` 只換第一處，`ReplaceMode::All` 換全部。
- **理由**：EXE 的特徵碼是特定指令位置，全域替換可能誤傷其他剛好相同的位元組；資料檔（MKF）則相反，同一筆數值可能合法地出現多次且都該改。Python 版用副檔名判斷，這裡改成呼叫端明示。
- **代價**：新增目標檔時要自己想清楚該用哪一種，不會自動幫你決定。

#### 備份不覆蓋

- **決定**：`backup_file()` 只在 `.bak` 不存在時建立備份。
- **理由**：使用者重複執行是常態。若每次都覆蓋備份，第二次執行後就再也回不到原版。
- **代價**：使用者若手動改壞了 `.bak`，程式不會察覺。

---

## 6. 測試

```powershell
cd src-tauri
cargo test
```

| 分類 | 涵蓋範圍 |
| :--- | :--- |
| 單元測試（`src/patch/`） | 十六進位解析、替換的兩種模式與不重疊語意、備份不覆蓋、沒命中就不寫檔、4 條特徵碼原始與替換等長、光碟版命中 2 條磁片版跳過 2 條、重跑不再變動、找不到主程式時回報錯誤、摘要格式 |
| 整合測試（`tests/oracle.rs`） | 拿真實遊戲檔跑完整流程 |

### 會被略過的測試

`tests/oracle.rs` 需要真實的遊戲檔，而**遊戲原始檔不進版控**（版權）。未設定環境變數時它會印出 `⏭ 略過` 並通過——**這代表沒測到，不代表測過了**。

```powershell
$env:RICH2_GAME_DIR = 'D:\path\to\two'    # 未修改的遊戲目錄，只會被複製，不會被改到
$env:RICH2_OUT_DIR  = 'D:\path\to\out'    # 產出位置，供外部比對雜湊
cargo test --test oracle -- --nocapture
```

### 與 Python 版的 oracle 比對

這是 Tauri 版能否取代 Python 版的唯一判準。做法是兩版各跑一份乾淨的遊戲目錄複本，再比對雜湊：

```powershell
# 1. Python 版（基準）
python -c "import sys; sys.path.insert(0, '.'); import main; main.run_patch(r'<py 複本>', lambda m: None, lambda m: sys.exit(1))"

# 2. Rust 版
cd src-tauri
$env:RICH2_GAME_DIR = '<原始遊戲目錄>'; $env:RICH2_OUT_DIR = '<rs 複本>'
cargo test --test oracle -- --nocapture

# 3. 比對
Get-FileHash '<py 複本>\RUN.EXE', '<rs 複本>\RUN.EXE' -Algorithm SHA256
```

**2026-08-06 實測結果：`RUN.EXE` 與 `RUN.EXE.bak` 的 SHA-256 兩版完全相同，整個目錄逐檔比對也無差異，日誌逐行一致。**

---

## 7. 建置與產物

```powershell
npm run tauri build
```

第一次要編譯整個 Tauri 相依樹，約 6–7 分鐘。`src-tauri/target/` 會長到 1.3 GB 左右；若也跑過 `cargo test`（debug profile 另外一份），總計約 4.4 GB。

**產物**（2026-08-06 實測）

| 產物 | 位置 | 大小 |
| :--- | :--- | ---: |
| portable exe | `src-tauri/target/release/rich2-patch.exe` | 3.05 MB |
| NSIS 安裝檔 | `src-tauri/target/release/bundle/nsis/` | 1.07 MB |

對照 Python 版的 9.70 MB，體積砍掉約七成——這正是這次遷移的主要動機。

Rust 的 release profile（`src-tauri/Cargo.toml`）刻意為體積調校：`opt-level = "s"`、`lto = true`、`codegen-units = 1`、`panic = "abort"`、`strip = true`，與 RICH2_EDITOR 同一組設定。

> **已知落差**：產物命名與簽章尚未接上，仍不符合
> [docs/rules/RELEASE_RULES.md](docs/rules/RELEASE_RULES.md) §2.1 要求的
> `[RICH2_PATCH][v1.0.0][Portable].exe` 格式。發佈前必須處理（遷移計畫步驟 6）。

**Python 版的打包**（保留期間仍可用）

```powershell
.\build.ps1                # 走 rich2_patch.spec，不要直接 pyinstaller main.py
```

### 版本號

**單一來源**：`package.json` 的 `version`

| 位置 | 欄位 | 方式 |
| :--- | :--- | :--- |
| `package.json` | `version` | 手動（單一來源） |
| `src-tauri/tauri.conf.json` | `version` | 手動 |
| `src-tauri/Cargo.toml` | `package.version` | 手動 |
| `src-tauri/Cargo.lock` | `rich2-patch` 的 `version` | 自動（`cargo build` 更新） |
| `file_version_info.txt` | `filevers` / `FileVersion` / `ProductVersion` | 手動（Python 版專用，移除該版後一併刪除） |
| 產物檔名 | — | 自動（Tauri 由 `tauri.conf.json` 讀取） |

發佈前依 [docs/rules/VERSION_RULES.md](docs/rules/VERSION_RULES.md) §7 逐項核對。

---

## 8. 分支、commit 與 PR 慣例

- **主分支**：`main`
- **開分支**：從 `main` 開，功能用 `feat/<描述>`、修正用 `fix/<描述>`。
- **commit 訊息**：首行為繁中祈使句摘要，必要時空一行後補理由。

### 舊實作的保留

`main` 走 Rust + Tauri 版，Python + tkinter 版依 `docs/rules/DEVELOPER_RULES.md` §4.3 以分支保留：

| 分支 | 內容 | 保留原因 | 解除條件 |
| :--- | :--- | :--- | :--- |
| `legacy/python-tkinter` | 遷移前的完整 Python + tkinter 實作 | 是驗證 Tauri 版正確性的基準（oracle）——對同一份 `RUN.EXE`，兩版產出的檔案必須逐位元組相同 | 上述比對通過，且 Tauri 版實機驗收完成後 |

**該分支不再接受新功能**，僅在有明確理由時接受修正。**不得刪除**。

`main` 上也暫時保留一份 Python 版的檔案，方便就地做 oracle 比對（見 §6）；驗收通過後移除。

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

宣告在 `src-tauri/capabilities/default.json`：

| 要求的權限 | 為什麼需要 |
| :--- | :--- |
| `core:default` | Tauri 基本功能 |
| `dialog:allow-open` | 讓使用者用系統對話框挑選遊戲資料夾 |

⚠ **前端刻意沒有任何 `fs` 權限。** 所有檔案讀寫都在 Rust 端完成，前端拿到的只是一個路徑字串。這是本專案與 RICH2_EDITOR 最主要的差異——那邊因為要同時支援瀏覽器版，不得不開 `fs:scope: **`。

新增權限前先問：這件事能不能在 Rust 端做完？可以的話就不要開給前端。

程式不連網、不寫登錄檔、不需要管理員權限。

### 9.3 依賴來源與鎖檔

- `package-lock.json` 與 `src-tauri/Cargo.lock` **都進版控**。
- 安裝一律用 **`npm ci`**（依鎖檔安裝，結果可重現），不要用 `npm install`。
- 前端只有 4 個直接相依（Tauri API、dialog plugin、Vite、Tailwind 及其型別工具），刻意維持精簡——這是 patcher 能只有 3 MB 的原因之一。
- Python 版保留期間，其相依只有 PyInstaller（僅打包用）。

### 9.4 破壞性操作的保護

| 操作 | 影響的資料 | 可回復機制 |
| :--- | :--- | :--- |
| 改寫 `RUN.EXE` | 使用者的遊戲主程式 | 先複製為 `RUN.EXE.bak`；**若 `.bak` 已存在則不覆蓋**，確保永遠保留最原始的版本。還原方式為把 `.bak` 改名回原檔名。 |

修改任何會寫入使用者檔案的程式碼時，都必須維持這個「備份優先、不覆蓋既有備份」的原則。`patch_binary()` 另有一道保護：**只有在資料真的改變時才寫檔**，重跑不會產生無謂的寫入。

---

## 10. 已知陷阱

#### 安裝完 rustup 後，已開著的終端機找不到 cargo

- **症狀**：建置時出現 `cargo: command not found` 或 `cargo not found`，但 rustup 確實裝好了。
- **原因**：rustup 安裝完只更新系統的 PATH，不會影響已經開著的 shell 工作階段。
- **處置**：重開終端機。

#### 第一次建置要六分鐘以上，且吃掉 1.3 GB

- **症狀**：`cargo test` 或 `npm run tauri build` 長時間沒有輸出。
- **原因**：整個 Tauri 相依樹要從頭編譯，release profile 又開了 `lto = true` 與 `codegen-units = 1`。debug 與 release 是兩份獨立的產物，都跑過的話 `target/` 會到 4.4 GB。
- **處置**：正常現象。**不要**隨手刪 `src-tauri/target/`，刪掉下次又要重來一遍。

#### 特徵碼的替換長度必須與原始長度相同

- **症狀**：patch 後遊戲直接當掉或行為完全錯亂。
- **原因**：EXE 裡的特徵碼是機器碼，替換長度不同會讓後面所有指令位移。
- **處置**：`src/patch/rich2.rs` 有一條單元測試專門守這件事（`四條特徵碼的長度必須等長`）。新增特徵碼時**不要**繞過它。

#### Steam 典藏版只會命中一半的特徵碼

- **症狀**：日誌顯示四條特徵碼中兩條「成功」、兩條「跳過 (找不到特徵碼或已修改)」。
- **原因**：磁片版與光碟版的偏移位址不同，程式兩套都試。任一版本本來就只會命中對應的那兩條。
- **處置**：這是正常行為，不是錯誤。判斷成功與否要看**是否有任何一條成功**，不是看是否四條全中。

#### 改動引擎後忘了跑 oracle 比對

- **症狀**：單元測試全過，但實際產出與 Python 版不同。
- **原因**：單元測試用的是合成資料，涵蓋不到真實 EXE 的所有情況。
- **處置**：動到 `src/patch/` 的任何邏輯後，**必須**依 §6 重跑一次 oracle 比對。這是 Python 版還留著的唯一理由。

#### 直接用 `pyinstaller main.py` 打包 Python 版，EXE 會肥好幾 MB

- **症狀**：Python 版打包成功，但產出的 EXE 明顯大於預期。
- **原因**：`.spec` 裡的模組排除清單與 Tcl/Tk 資源裁切只有走 `.spec` 才會生效。
- **處置**：一律走 `rich2_patch.spec`，或直接用 `build.ps1`。

---

## 相關文件

- 使用說明：[README.md](README.md)
- 變更紀錄：[CHANGELOG.md](CHANGELOG.md)
- 遷移計畫：[TAURI_MIGRATION.md](TAURI_MIGRATION.md)
- 文件與發佈規範：[docs/rules/](docs/rules/)
