# 大富翁2 Patch (Rich Patch Series)

### 本工具主要針對 Steam 典藏版修正

**🛠️ 本次更新與修正核心**

1. 主程式修正
- 多人競賽解鎖：多人地圖現在也可以一個人玩（對抗電腦）。

2. 版本相容性說明
- Steam 典藏版：已完成測試確認。
- 磁片版：腳本內包含對應之特徵碼替換邏輯，但因手邊無實體檔案，目前處於「未測試」狀態。

3. 操作指南
- 將本修正檔 (rich2_patch.exe) 放入遊戲的 two 資料夾並執行。
- 開啟後確認上方「遊戲目錄」是否正確，需要的話按「瀏覽...」重新指定。
- 按下「開始」，程式會自動完成 Hex 修改，過程與結果會顯示在下方日誌區。
- 原始檔案會自動備份為 `*.bak`，重跑不會覆蓋最初的備份。

4. 致謝與來源參考
- 核心特徵碼參考：青衫之友交流網 [連結](https://chiuinan.github.io/game/game/intro/ch/c43/rich2/index.htm)

---

**📦 自行打包**

```bash
pip install -r requirements.txt
./build.sh     # Linux / WSL (透過 Wine)
build.bat      # Windows
```

打包一律走 `rich2_patch.spec`，內含模組排除清單以控制 EXE 體積。
