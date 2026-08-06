//! 拿真實遊戲檔跑一遍 Rust 引擎，供與 Python 版做逐位元組比對。
//!
//! 遊戲原始檔**不進版控**（版權），所以這個測試預設會被略過而不是失敗——與
//! RICH2_EDITOR 的測試慣例一致。
//!
//! 用法：
//! ```powershell
//! $env:RICH2_GAME_DIR = 'D:\path\to\two'      # 未修改的遊戲目錄，會被複製，不會被改到
//! $env:RICH2_OUT_DIR  = 'D:\path\to\out'      # 產出位置，供外部比對雜湊
//! cargo test --test oracle -- --nocapture
//! ```

use std::fs;
use std::path::{Path, PathBuf};

use rich2_patch::patch::{rich2, Reporter};

struct StdoutReporter;

impl Reporter for StdoutReporter {
    fn log(&self, message: &str, level: &str, step: Option<u32>) {
        let tag = match step {
            Some(s) => format!("[STEP {s}/{}]", rich2::TOTAL_STEPS),
            None => "[DETAILS]".to_string(),
        };
        println!("[{level}]{tag} {message}");
    }
}

fn copy_dir(from: &Path, to: &Path) -> std::io::Result<()> {
    fs::create_dir_all(to)?;
    for entry in fs::read_dir(from)? {
        let entry = entry?;
        let target = to.join(entry.file_name());
        if entry.file_type()?.is_dir() {
            copy_dir(&entry.path(), &target)?;
        } else {
            fs::copy(entry.path(), &target)?;
        }
    }
    Ok(())
}

#[test]
fn 對真實遊戲檔執行() {
    let Ok(game_dir) = std::env::var("RICH2_GAME_DIR") else {
        println!("⏭ 略過：未設定 RICH2_GAME_DIR（遊戲原始檔不進版控，這不算失敗）");
        return;
    };

    let out_dir = std::env::var("RICH2_OUT_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| std::env::temp_dir().join("rich2_patch_oracle"));

    let _ = fs::remove_dir_all(&out_dir);
    copy_dir(Path::new(&game_dir), &out_dir).expect("複製遊戲目錄失敗");

    let summary = rich2::run_patch(&out_dir, &StdoutReporter).expect("執行失敗");
    println!("\n{summary}");

    let exe = rich2::patch_exe(&out_dir, &StdoutReporter, 1);
    assert!(exe.is_ok(), "重跑不應出錯");
    assert!(
        !exe.unwrap(),
        "重跑應該不再有任何變更（特徵碼已被改掉）"
    );

    let bak = out_dir.join("RUN.EXE.bak");
    assert!(bak.exists(), "應該產生 RUN.EXE.bak");
    assert_eq!(
        fs::read(&bak).unwrap(),
        fs::read(Path::new(&game_dir).join("Run.exe")).unwrap(),
        ".bak 必須逐位元組等於原始檔"
    );

    println!("\n產出位置：{}", out_dir.display());
}
