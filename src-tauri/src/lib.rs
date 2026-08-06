// 大富翁2 Patch —— Tauri 外殼與指令。
//
// 與 RICH2_EDITOR 刻意相反：patch 引擎放在 Rust（`patch` 模組），前端只負責畫面與事件。
// patcher 沒有瀏覽器版的需求，把二進位處理留在 Rust 就不必把檔案系統權限開放給前端，
// 前端只需要 dialog 來讓使用者挑資料夾（見 capabilities/default.json）。

pub mod patch;

use std::path::Path;

use serde::Serialize;
use tauri::{AppHandle, Emitter};

use patch::{rich2, Reporter, FATAL};

/// 送到前端的日誌事件。
#[derive(Clone, Serialize)]
struct LogPayload {
    level: String,
    message: String,
    /// 有值代表這是一個步驟的開始，前端應同時推進進度條
    step: Option<u32>,
    total: u32,
}

/// 把引擎的輸出轉成 Tauri 事件。
struct TauriReporter {
    app: AppHandle,
}

impl Reporter for TauriReporter {
    fn log(&self, message: &str, level: &str, step: Option<u32>) {
        // 同時印到終端機，格式與 Python 版一致，方便開發時兩版並排對照
        let tag = match step {
            Some(s) => format!("[STEP {s}/{}]", rich2::TOTAL_STEPS),
            None => "[DETAILS]".to_string(),
        };
        println!("[{level}]{tag} {message}");

        let _ = self.app.emit(
            "patch://log",
            LogPayload {
                level: level.to_string(),
                message: message.to_string(),
                step,
                total: rich2::TOTAL_STEPS,
            },
        );
    }
}

/// 對指定的遊戲目錄執行全套 patch。
///
/// 放在背景執行緒跑：目前 RICH2 只需毫秒級，但同一套介面之後要給 RICH3 用，
/// 那邊光是產生日曆就要數十秒，不能卡住 UI 執行緒。
#[tauri::command]
async fn run_patch(app: AppHandle, target_dir: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let reporter = TauriReporter { app };
        match rich2::run_patch(Path::new(&target_dir), &reporter) {
            Ok(summary) => Ok(summary),
            Err(err) => {
                let message = format!("幹，Patch 發生嚴重錯誤：\n{err}");
                reporter.log(&message, FATAL, None);
                Err(message)
            }
        }
    })
    .await
    .map_err(|err| format!("背景執行緒異常結束：{err}"))?
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![run_patch])
        .run(tauri::generate_context!())
        .expect("Tauri 啟動失敗");
}
