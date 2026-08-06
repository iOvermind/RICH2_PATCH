// patch 模組的組成。
//
// `engine` 是 Rich Patch Series 兩支程式**逐字元相同**的共用引擎，改動時務必同步；
// 其餘模組是本專案專屬的。

pub mod engine;
pub mod rich2;

pub use engine::*;
