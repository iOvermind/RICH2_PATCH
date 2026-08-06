// 《大富翁2》專屬的 patch 步驟。
//
// 特徵碼逐條移植自 Python 版 `main.py`，**中文名稱字串刻意保持一字不差**，這樣兩版的
// 日誌可以直接並排對照（見 TAURI_MIGRATION.md 步驟 2 的驗收方式）。

use std::io;
use std::path::Path;

use super::{
    backup_file, format_report, patch_binary, find_target, ReplaceMode, Reporter, Rule, DONE, ERROR,
};

pub const GAME_NAME: &str = "大富翁2";
pub const TOTAL_STEPS: u32 = 1;

/// `RUN.EXE` 的 4 條特徵碼。
///
/// 磁片版與光碟典藏版的偏移位址不同，兩套都列出來逐一嘗試——任一版本本來就只會命中
/// 屬於它的那兩條，另外兩條顯示「跳過」是正常的，不是錯誤。
fn exe_rules() -> Vec<Rule> {
    vec![
        // 磁片版
        Rule::new(
            "多人競賽也可一個人玩 (磁片版 1/2)",
            &[("83 3E E8 10 00 7E", "83 3E E8 10 01 7E")],
        ),
        Rule::new(
            "多人競賽也可一個人玩 (磁片版 2/2)",
            &[("83 3E E8 10 01 75 03", "83 06 E8 10 01 EB 03")],
        ),
        // 光碟典藏版
        Rule::new(
            "多人競賽也可一個人玩 (光碟版 1/2)",
            &[("83 3E 36 11 00 7E", "83 3E 36 11 01 7E")],
        ),
        Rule::new(
            "多人競賽也可一個人玩 (光碟版 2/2)",
            &[("83 3E 36 11 01 75 03", "83 06 36 11 01 EB 03")],
        ),
    ]
}

/// 步驟 1：修改主程式。
pub fn patch_exe(target_dir: &Path, reporter: &dyn Reporter, step: u32) -> io::Result<bool> {
    reporter.log("開始尋找主程式並進行修改...", super::INFO, Some(step));

    // 大富翁2 的主程式為 RUN.EXE
    let exe_target = match find_target(target_dir, &["RUN.EXE", "run.exe"]) {
        Some(path) => path,
        None => {
            reporter.log(
                "找不到 RUN.EXE！請確認檔案在目標目錄。",
                ERROR,
                None,
            );
            return Ok(false);
        }
    };

    reporter.info(&format!("找到主程式：{}", exe_target.display()));
    backup_file(&exe_target, reporter)?;

    patch_binary(&exe_target, &exe_rules(), ReplaceMode::First, reporter)
}

/// 主幹流程。回傳給使用者看的執行摘要。
pub fn run_patch(target_dir: &Path, reporter: &dyn Reporter) -> io::Result<String> {
    let exe_res = patch_exe(target_dir, reporter, 1)?;

    let report = format_report(&[("主程式 (EXE)", exe_res)]);
    reporter.log("所有任務完工！爽啦！", DONE, Some(TOTAL_STEPS));

    Ok(format!(
        "{GAME_NAME} 全套 Patch 執行完畢！\n\n【執行摘要】\n{report}"
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::patch::{hex, INFO};
    use std::cell::RefCell;
    use std::fs;

    struct Collector {
        lines: RefCell<Vec<String>>,
    }
    impl Reporter for Collector {
        fn log(&self, message: &str, level: &str, _step: Option<u32>) {
            self.lines.borrow_mut().push(format!("[{level}] {message}"));
        }
    }

    #[test]
    fn 四條特徵碼的長度必須等長() {
        // 替換碼與原始碼長度不同會讓後面的指令整個位移，那是災難性的
        for rule in exe_rules() {
            for (from, to) in &rule.targets {
                assert_eq!(
                    from.len(),
                    to.len(),
                    "特徵碼「{}」的原始與替換長度不一致",
                    rule.name
                );
            }
        }
    }

    #[test]
    fn 光碟版命中兩條磁片版跳過兩條() {
        let dir = std::env::temp_dir().join(format!("rich2_rules_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();

        // 造一份只含光碟版特徵碼的假 EXE
        let mut fake = vec![0u8; 64];
        fake.extend_from_slice(&hex("83 3E 36 11 00 7E"));
        fake.extend_from_slice(&vec![0u8; 32]);
        fake.extend_from_slice(&hex("83 3E 36 11 01 75 03"));
        fake.extend_from_slice(&vec![0u8; 64]);

        let exe = dir.join("RUN.EXE");
        fs::write(&exe, &fake).unwrap();

        let reporter = Collector {
            lines: RefCell::new(Vec::new()),
        };
        let changed = patch_exe(&dir, &reporter, 1).unwrap();
        assert!(changed);

        let lines = reporter.lines.borrow().clone();
        let hit = lines.iter().filter(|l| l.contains("[成功]")).count();
        let skipped = lines.iter().filter(|l| l.contains("[跳過]")).count();
        assert_eq!(hit, 2, "光碟版應命中 2 條");
        assert_eq!(skipped, 2, "磁片版應跳過 2 條");
        assert!(lines.iter().any(|l| l.contains("已儲存修改 (2/4 項)")));

        // 檔案長度不可改變
        let patched = fs::read(&exe).unwrap();
        assert_eq!(patched.len(), fake.len());
        assert!(fs::metadata(dir.join("RUN.EXE.bak")).is_ok());

        // 重跑一次：四條全部跳過、檔案不再變動
        let reporter2 = Collector {
            lines: RefCell::new(Vec::new()),
        };
        let changed2 = patch_exe(&dir, &reporter2, 1).unwrap();
        assert!(!changed2);
        assert_eq!(fs::read(&exe).unwrap(), patched);
        assert_eq!(fs::read(dir.join("RUN.EXE.bak")).unwrap(), fake);

        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn 找不到主程式時回報錯誤而非崩潰() {
        let dir = std::env::temp_dir().join(format!("rich2_noexe_test_{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();

        let reporter = Collector {
            lines: RefCell::new(Vec::new()),
        };
        let changed = patch_exe(&dir, &reporter, 1).unwrap();

        assert!(!changed);
        assert!(reporter
            .lines
            .borrow()
            .iter()
            .any(|l| l.starts_with(&format!("[{ERROR}]")) && l.contains("找不到 RUN.EXE")));

        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn 摘要格式與_python_版一致() {
        assert_eq!(format_report(&[("主程式 (EXE)", true)]), "✅ 主程式 (EXE): 成功處理");
        assert_eq!(
            format_report(&[("主程式 (EXE)", false)]),
            "⚠️ 主程式 (EXE): 未變動或失敗"
        );
        let _ = INFO;
    }
}
