# 大富翁2 Patch 開發者文件

> 這份文件給**要修改這個專案的人**。使用說明請看 [README.md](README.md)。
> 文件與發佈規範見 [docs/rules/](docs/rules/)。

> **遷移已完成。** `main` 是 Rust + Tauri，發佈中的版本也是它。Python + tkinter 版
> 已從 `main` 移除，完整保留在 `legacy/python-tkinter` 分支（見 §8）。
> 過程與驗收記錄在 [TAURI_MIGRATION.md](TAURI_MIGRATION.md)。

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

**作業系統限制**：產物僅供 Windows。

要重跑 oracle 比對時才需要 Python 3.10 以上（`main` 上已無 Python 檔案，見 §6）。

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
│  └─ style.css             Tailwind 設定；色票引用 docs/rules/tokens.css
├─ src-tauri/
│  ├─ Cargo.toml            Rust 相依與 release profile
│  ├─ tauri.conf.json       視窗、bundle、identifier
│  ├─ capabilities/         Tauri 權限宣告（見 §9.2）
│  ├─ icons/                由 icon.png 產生的全套圖示
│  ├─ src/
│  │  ├─ main.rs            進入點，只呼叫 lib
│  │  ├─ lib.rs             Tauri 外殼、指令、事件轉送
│  │  └─ patch/
│  │     ├─ mod.rs          模組宣告
│  │     ├─ engine.rs       ⚠ 共用引擎，與 RICH3_PATCH **逐字元相同**
│  │     └─ rich2.rs        RUN.EXE 的 4 條特徵碼與主幹流程
│  └─ tests/oracle.rs       拿真實遊戲檔跑一遍，供與 Python 版比對
├─ build.ps1                建置與發佈打包（含版本號一致性檢查）
├─ release/                 發佈產物，不進版控
└─ docs/rules/              文件與發佈規範（正典在 DEV_TEMPLATE）
```

---

## 5. 架構與關鍵設計決策

### 模組職責

| 模組 | 職責 | 依賴 |
| :--- | :--- | :--- |
| `patch::engine` | 共用引擎：特徵碼比對、備份、寫檔、摘要格式 | **不依賴 Tauri** |
| `patch::rich2` | 《大富翁2》專屬：4 條特徵碼與主幹流程 | `patch::engine` |
| `lib.rs` | Tauri 外殼：指令、把引擎輸出轉成事件 | 以上兩者 + Tauri |
| `src/main.ts` | 前端：畫面與事件 | Tauri API |

**Tauri 指令**

| 指令 | 作用 |
| :--- | :--- |
| `run_patch(targetDir)` | 對指定目錄執行全套 patch，回傳執行摘要。過程中持續送 `patch://log` 事件 |
| `default_dir()` | 回傳程式所在目錄，供啟動時預填 |

### 關鍵決策

#### patch 引擎放 Rust，不放前端

- **決定**：所有二進位處理在 `src-tauri/src/patch/`，前端只負責畫面。
- **理由**：patcher 沒有瀏覽器版的需求，把引擎留在 Rust 就**不必把檔案系統權限開放給前端**——前端只需要 dialog 來挑資料夾（見 §9.2）。
- **代價**：與 RICH2_EDITOR 相反的分工，兩個專案的架構不能互相套用。那邊邏輯在前端 TypeScript，因為它要同時服務桌面版與瀏覽器版。

#### 共用引擎獨立成 `engine.rs`，與 RICH3_PATCH 逐字元相同

- **決定**：特徵碼比對、備份、寫檔、摘要格式放 `patch/engine.rs`；`patch/mod.rs` 只宣告模組。兩支 patcher 的 `engine.rs` **必須逐字元相同**，改動時同步複製。
- **理由**：兩支程式的引擎行為本來就該一致（同一套備份策略、同一種日誌格式、同一組替換語意）。放在同一個檔案而非各自實作，差異才不會悄悄長出來——可以直接用雜湊驗證。
- **代價**：改 `engine.rs` 一定要同時動兩個 repo；只有其中一邊需要的功能（例如 RICH3 的萬用位元組比對）也得寫進共用檔。

#### 引擎以 `Reporter` trait 與 Tauri 解耦

- **決定**：`patch` 模組不引用任何 Tauri 型別，輸出一律走 `Reporter` trait；`lib.rs` 提供 Tauri 實作，測試提供收集用的實作。
- **理由**：**這是能做 oracle 比對的前提**。同一份引擎要能在沒有視窗的情況下跑，才能和 Python 版比對輸出（見 §6）。這也延續了 Python 版「介面與邏輯以回呼解耦」的決策。
- **代價**：多一層間接；加新訊息時要記得帶 `step` 才會推進進度條。

#### 替換範圍由 `ReplaceMode` 決定，而非硬寫

- **決定**：`ReplaceMode::First` 只換第一處，`ReplaceMode::All` 換全部。
- **理由**：EXE 的特徵碼是特定指令位置，全域替換可能誤傷其他剛好相同的位元組；資料檔（MKF）則相反，同一筆數值可能合法地出現多次且都該改。Python 版用副檔名判斷，這裡改成呼叫端明示。
- **代價**：新增目標檔時要自己想清楚該用哪一種，不會自動幫你決定。

#### 只跟 RICH2_EDITOR 共用色票與字體，版型完全自己來

- **決定**：`src/style.css` 的 `@theme` 與 RICH2_EDITOR 逐字相同（色票、字體堆疊），但版型是單欄小工具——目錄列（輸入框 + 瀏覽 + 開始，三者等高 `h-9`）、進度條、日誌區，視窗 520×480。**不套用** editor 那套三欄工作站版型。
- **理由**：兩者的體量差太多。editor 是 1500×950 的編輯工作站，patcher 是按一下就跑完的小工具。共用色票已足以讓人看出是同一系列，硬套版型只會讓小工具變得笨重。
- **代價**：兩個專案的畫面程式碼無法互相複製，只有設計 token 是共用的。

#### 前端不假設自己知道路徑存不存在

- **決定**：目錄的有效性一律由 Rust 端判斷（找不到 `RUN.EXE` 就送 `ERROR` 日誌），前端只把使用者挑的字串交出去。
- **理由**：前端沒有 `fs` 權限，本來就無從檢查；與其在前端猜，不如讓唯一有能力判斷的一方負責。
- **代價**：路徑錯誤時要等按下「開始」才會知道，不會在選擇當下就提示。

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

這是 Tauri 版能否取代 Python 版的判準。動到 `patch/` 之後**必須**重跑。

Python 版已從 `main` 移除，要跑基準時從分支取出到庫外：

```powershell
# 0. 取出 Python 基準版
git worktree add ..\rich2-oracle legacy/python-tkinter

# 1. Python 版（基準）
python -c "import sys; sys.path.insert(0, r'..\rich2-oracle'); import main; main.run_patch(r'<py 複本>', lambda m: None, lambda m: sys.exit(1))"

# 2. Rust 版
cd src-tauri
$env:RICH2_GAME_DIR = '<原始遊戲目錄>'; $env:RICH2_OUT_DIR = '<rs 複本>'
cargo test --test oracle -- --nocapture

# 3. 比對
Get-FileHash '<py 複本>\RUN.EXE', '<rs 複本>\RUN.EXE' -Algorithm SHA256
```

### 兩個層級都要驗

| 層級 | 驗什麼 | 怎麼跑 |
| :--- | :--- | :--- |
| 函式庫 | 引擎邏輯正確 | `cargo test --test oracle` |
| **發佈產物** | **打包、LTO、strip 之後行為仍相同** | 直接執行 `release\` 裡的 portable exe |

只驗函式庫是不夠的——中間隔著 Tauri 打包。產物層級要用 GUI 跑，關鍵在**取得前景視窗**：

```powershell
# Windows 不允許背景程序隨意搶前景，光呼叫 SetForegroundWindow 會被擋。
# 必須先 AttachThreadInput 把自己的輸入佇列接到目標與現有前景視窗的執行緒上。
AttachThreadInput(me, foreThread, true);
AttachThreadInput(me, targetThread, true);
ShowWindow(h, SW_RESTORE); BringWindowToTop(h); SetForegroundWindow(h);
```

沒做這步的話模擬點擊約有一半機率靜靜地不生效，看起來像程式沒反應。

**實測結果**

- 2026-08-06（函式庫層級）：`RUN.EXE` 與 `RUN.EXE.bak` 兩版 SHA-256 完全相同，整個目錄逐檔比對無差異，日誌逐行一致。
- 2026-08-07（產物層級）：實際發佈的 `RICH2_PATCH-v1.0.1-Portable.exe` 與 Python 版產出的 `RUN.EXE` **逐位元組相同**。

---

## 7. 建置與產物

```powershell
.\build.ps1                # 建置並收進 release\
.\build.ps1 -Sign          # 另外用自簽憑證簽章
.\build.ps1 -SkipInstall   # 跳過 npm ci，相依沒動過時較快
```

`build.ps1` 是一鍵流程：**先擋版本號不一致**（見下方「版本號」）→ `npm ci` → `tauri build` → 依規範命名收進 `release\` → 選擇性簽章 → 產生 `SHA256SUMS.txt` → 回報體積。

只要單純編譯的話也可以直接下 `npm run tauri build`，但產物會留在 `src-tauri/target/release/` 且是原始檔名，**不符合發佈規範**。

第一次要編譯整個 Tauri 相依樹，約 6–7 分鐘。`src-tauri/target/` 會長到 1.3 GB 左右；若也跑過 `cargo test`（debug profile 另外一份），總計約 4.4 GB。

**產物**（2026-08-06 實測，已簽章）

| 產物 | 大小 | 用途 |
| :--- | ---: | :--- |
| `release/RICH2_PATCH-v1.0.1-Portable.exe` | 3.06 MB | 免安裝，直接執行 |
| `release/RICH2_PATCH-v1.0.1-Setup.exe` | 1.08 MB | NSIS 安裝檔，裝到使用者目錄，不需要管理員 |
| `release/SHA256SUMS.txt` | — | 兩個產物的校驗碼，**必附**（RELEASE_RULES §4.3） |

命名依 [docs/rules/RELEASE_RULES.md](docs/rules/RELEASE_RULES.md) §2.1：只用 `A-Za-z0-9.-_`，因為 GitHub 會把其餘字元換成點，本機與線上檔名一旦不同，校驗碼就失去意義。`release/` 不進版控。

對照 Python 版的 9.70 MB，體積砍掉約七成——這正是這次遷移的主要動機。

**簽章**：走自簽憑證 `Overmind.pfx`（不進版控）。腳本會先找憑證存放區裡既有的 `CN=Overmind` 來用，沒有才簽發新的——舊版腳本每次找不到 pfx 就再簽一張，會在存放區裡累積同名憑證。

自簽憑證只是讓 EXE 帶上發行者名稱，**不具信任價值**：`Get-AuthenticodeSignature` 會回報「terminated in a root certificate which is not trusted」，使用者仍會看到 SmartScreen 警告。這件事在 README 的常見問題有對使用者說明，並要他們改用校驗碼確認來源。

Rust 的 release profile（`src-tauri/Cargo.toml`）刻意為體積調校：`opt-level = "s"`、`lto = true`、`codegen-units = 1`、`panic = "abort"`、`strip = true`，與 RICH2_EDITOR 同一組設定。

### 版本號

**單一來源**：`package.json` 的 `version`

| 位置 | 欄位 | 方式 |
| :--- | :--- | :--- |
| `package.json` | `version` | 手動（單一來源） |
| `src-tauri/tauri.conf.json` | `version` | 手動 |
| `src-tauri/Cargo.toml` | `package.version` | 手動 |
| `src-tauri/Cargo.lock` | `rich2-patch` 的 `version` | 自動（`cargo build` 更新） |
| 產物檔名 | — | 自動（`build.ps1` 讀取單一來源） |

**改版本號時，前三處都要手動改。** `build.ps1` 開頭會把三處讀出來比對，**不一致就直接中止**，這就是 [docs/rules/VERSION_RULES.md](docs/rules/VERSION_RULES.md) §2.3 說的「唯讀檢查」——版本號一律手動改，這道檢查負責攔住漏改的那一處。

---

## 8. 分支、commit 與 PR 慣例

- **主分支**：`main`
- **開分支**：從 `main` 開，功能用 `feat/<描述>`、修正用 `fix/<描述>`。
- **commit 訊息**：首行為繁中祈使句摘要，必要時空一行後補理由。

### 舊實作的保留

`main` 走 Rust + Tauri 版，Python + tkinter 版依 `docs/rules/DEVELOPER_RULES.md` §4.3 以分支保留：

| 分支 | 內容 | 保留原因 | 解除條件 |
| :--- | :--- | :--- | :--- |
| `legacy/python-tkinter` | 遷移前的完整 Python + tkinter 實作（含打包腳本與 `.spec`） | 是驗證 Tauri 版正確性的基準（oracle）。動到 `patch/` 之後要重跑 §6 的比對，屆時從這個分支取出 | **無**——這個分支永久保留 |

**該分支不再接受新功能**，僅在有明確理由時接受修正。**不得刪除**。

`main` 上**已無任何 Python 檔案**（2026-08-07 移除，驗收通過）。需要基準時用 `git worktree` 從分支取出，見 §6。

---

## 9. 安全與敏感資料

### 9.1 機密不進版控

| 項目 | 排除方式 | 本機該放哪 |
| :--- | :--- | :--- |
| 簽章憑證 `Overmind.pfx` | `.gitignore` 的 `*.pfx` | 專案根目錄，由建置腳本自動產生 |
| 遊戲原始檔（`*.EXE` / `*.MKF` / `*.PAT` / `*.bak`…） | `.gitignore` 逐項排除 | 庫外，或 `original/` / `dist/` 等已忽略的目錄 |

⚠ **憑證密碼 `overmind` 以明文寫在 `build.ps1` 中。** 這是刻意的權衡：該憑證為自簽、僅用於讓 EXE 帶上發行者名稱，本身不具信任價值，密碼公開不造成額外風險。**因此這張憑證不得用於任何其他用途**；若日後改用有實際信任價值的憑證，密碼必須改由環境變數或憑證存放區提供。

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
- Python 基準版只用標準函式庫，沒有執行期相依；它在 `legacy/python-tkinter` 分支上。

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
- **原因**：整個 Tauri 相依樹要從頭編譯，其中 `windows` / `windows-sys` 那組 API 綁定特別耗時。release profile 又開了 `lto = true` 與 `codegen-units = 1`。debug 與 release 是兩份獨立的產物，都跑過的話 `target/` 會到 4.4 GB。
- **處置**：正常現象。**完全冷啟動**（乾淨的 `target/`）實測要 **30 分鐘以上**；本文件其他地方寫的 6–7 分鐘是 `target/` 已有暖機資料時的數字，不要拿來當基準。**不要**隨手刪 `src-tauri/target/`，刪掉下次又要重來一遍。

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

#### 編輯 `build.ps1` 後整支腳本變成語法錯誤

- **症狀**：執行 `build.ps1` 出現一堆莫名其妙的 `Unexpected token`、`Missing closing '}'`，錯誤都指向含中文的行。
- **原因**：Windows PowerShell 5.1 讀 `.ps1` 預設用**系統 ANSI 碼頁**。檔案若存成無 BOM 的 UTF-8，中文會被拆壞、直接變成語法錯誤。
- **處置**：`build.ps1` **必須**存成 **UTF-8 with BOM**（`.gitattributes` 另有 `*.ps1 text eol=crlf`）。很多編輯器與工具預設存無 BOM，改完務必確認：
  ```powershell
  $b = [System.IO.File]::ReadAllBytes('build.ps1')
  $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF   # 要是 True
  ```
  注意這是 `.ps1` 專屬的例外——Markdown 文件依規範一律 UTF-8 **無** BOM。

#### `npm` 或 `cargo` 明明跑成功，腳本卻中止

- **症狀**：`build.ps1` 在建置那步失敗，訊息是 `NativeCommandError`，內容卻是 `Info Looking up installed tauri packages...` 這種正常的進度訊息。
- **原因**：PowerShell 5.1 會把原生指令寫到 stderr 的每一行包成 `ErrorRecord`；npm 與 cargo 都把進度訊息寫到 stderr。配上 `$ErrorActionPreference = 'Stop'`，成功的指令也會被當成失敗。
- **處置**：原生指令一律走 `build.ps1` 裡的 `Invoke-Native`，它會暫時把 `ErrorActionPreference` 切成 `Continue`，**成敗只看離開碼**。不要直接呼叫再用 `$?` 判斷。

---

## 相關文件

- 使用說明：[README.md](README.md)
- 介面規格：[INTERFACE.md](INTERFACE.md)
- 變更紀錄：[CHANGELOG.md](CHANGELOG.md)
- 遷移計畫：[TAURI_MIGRATION.md](TAURI_MIGRATION.md)
- 文件與發佈規範：[docs/rules/](docs/rules/)
