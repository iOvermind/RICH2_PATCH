// 前端進入點。
//
// 這裡只負責畫面與事件；所有二進位處理都在 Rust（src-tauri/src/patch/）。
// 這個分工是刻意的，與 RICH2_EDITOR 相反——patcher 沒有瀏覽器版的需求，
// 把引擎放 Rust 就不必開放檔案系統權限給前端。

import './style.css';

// 步驟 3 會在這裡掛上目錄選擇、開始按鈕、進度條與日誌區。
console.info('[rich2_patch] 前端已載入');
