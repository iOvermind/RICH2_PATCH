# 變更紀錄 (Changelog)

本檔案記錄本專案所有值得使用者知道的變更。

格式依 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，版本號依語意化版本
（見 [docs/rules/VERSION_RULES.md](docs/rules/VERSION_RULES.md)）。日期格式為 `YYYY-MM-DD`。

> 2026-03-28 曾發佈 `Rich2_Patch_v1.0` 預覽版。該 tag 不符合現行命名慣例，將於
> `v1.0.0` 發佈時一併移除（見 [TAURI_MIGRATION.md](TAURI_MIGRATION.md)），因此不列入
> 本紀錄。以下 `[Unreleased]` 即 `v1.0.0` 將包含的內容。

## [Unreleased]

### Added (新增)
- 解鎖多人競賽地圖，原本需要湊人數的地圖現在可以一個人玩，對手換成電腦。
- 修改前自動把 `RUN.EXE` 備份為 `RUN.EXE.bak`；重複執行不會覆蓋最初的備份，隨時可以還原回原版。
- 可以用「瀏覽...」自行指定遊戲資料夾，不必把程式放進遊戲目錄再執行。
- 視窗內顯示逐步日誌與進度，看得到每一項修改是成功還是跳過。
