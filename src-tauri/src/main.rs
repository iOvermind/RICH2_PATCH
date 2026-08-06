// 大富翁2 Patch 的 Tauri 外殼。
//
// 與 RICH2_EDITOR 刻意相反：patch 引擎放在 Rust（src-tauri/src/patch/），前端只負責
// 畫面與事件。patcher 沒有瀏覽器版的需求，把二進位處理留在 Rust 就不必把整個檔案
// 系統的權限開放給前端——前端只需要 dialog 來讓使用者挑資料夾。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .run(tauri::generate_context!())
        .expect("Tauri 啟動失敗");
}
