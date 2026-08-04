import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import shutil
import re

# =====================================================================
# 專案設定 (Rich Patch Series)
# =====================================================================
GAME_NAME = "大富翁2"
APP_TITLE = f"{GAME_NAME} Patch"
TOTAL_STEPS = 1

# =====================================================================
# 日誌回呼系統與暫存狀態
# =====================================================================
_log_callback = None
_progress_callback = None

def set_callbacks(log_cb, prog_cb):
    global _log_callback, _progress_callback
    _log_callback = log_cb
    _progress_callback = prog_cb

def emit_log(msg, step=None, status="INFO"):
    """
    更新終端機輸出，並透過回呼函數更新 UI，實現介面與邏輯解耦
    """
    step_tag = f"[STEP {step}/{TOTAL_STEPS}]" if step else "[DETAILS]"
    print(f"[{status}]{step_tag} {msg}", flush=True)

    if _log_callback:
        _log_callback(msg, status)
    if step and _progress_callback:
        _progress_callback(step, TOTAL_STEPS)

# =====================================================================
# 共用工具
# =====================================================================
def backup_file(filename):
    if not os.path.exists(filename):
        return False
    bak_name = filename + ".bak"
    if not os.path.exists(bak_name):
        shutil.copy2(filename, bak_name)
        emit_log(f"已建立備份 {bak_name}")
    else:
        emit_log(f"{bak_name} 備份已存在，跳過覆蓋以保留最原始檔案")
    return True

def find_target(target_dir, names):
    """在目標目錄中不分大小寫尋找第一個存在的檔案"""
    for name in names:
        path = os.path.join(target_dir, name)
        if os.path.exists(path):
            return path
    return None

def patch_binary(filename, patches):
    with open(filename, "rb") as f:
        data = f.read()

    emit_log(f"開始分析與 Patch {filename} ...")
    modified_data = data
    success_count = 0

    for patch in patches:
        name = patch['name']
        success = False

        if patch.get('is_regex'):
            pattern = re.compile(patch['pattern'], re.DOTALL)
            if pattern.search(modified_data):
                modified_data = pattern.sub(patch['replacement'], modified_data, count=1)
                success = True
        else:
            for target, replacement in patch['targets']:
                if target in modified_data:
                    if filename.upper().endswith(".MKF"):
                        modified_data = modified_data.replace(target, replacement)
                    else:
                        # 只替換第一次出現的特徵碼
                        modified_data = modified_data.replace(target, replacement, 1)
                    success = True
                    break

        if success:
            emit_log(f"[成功] {name}")
            success_count += 1
        else:
            emit_log(f"[跳過] {name} (找不到特徵碼或已修改)", status="WARN")

    if data != modified_data:
        with open(filename, "wb") as f:
            f.write(modified_data)
        emit_log(f"[完成] {filename} 已儲存修改 ({success_count}/{len(patches)} 項).", status="SUCCESS")
        return True
    else:
        emit_log(f"[提示] {filename} 沒有發生任何變更。", status="WARN")
        return False

def format_report(results):
    """把各步驟成果整理成統一格式的摘要"""
    return "\n".join(
        f"{'✅' if ok else '⚠️'} {label}: {'成功處理' if ok else '未變動或失敗'}"
        for label, ok in results
    )

# =====================================================================
# 核心處理函數
# =====================================================================
def patch_exe(target_dir, step):
    emit_log("開始尋找主程式並進行修改...", step=step)
    # 大富翁2 的主程式為 RUN.EXE
    exe_target = find_target(target_dir, ["RUN.EXE", "run.exe"])

    if not exe_target:
        emit_log("找不到 RUN.EXE！請確認檔案在目標目錄。", status="ERROR")
        return False

    emit_log(f"找到主程式：{exe_target}")
    backup_file(exe_target)

    exe_patches = [
        # 磁片版
        {"name": "多人競賽也可一個人玩 (磁片版 1/2)", "targets": [(bytes.fromhex("83 3E E8 10 00 7E"), bytes.fromhex("83 3E E8 10 01 7E"))]},
        {"name": "多人競賽也可一個人玩 (磁片版 2/2)", "targets": [(bytes.fromhex("83 3E E8 10 01 75 03"), bytes.fromhex("83 06 E8 10 01 EB 03"))]},
        # 光碟典藏版
        {"name": "多人競賽也可一個人玩 (光碟版 1/2)", "targets": [(bytes.fromhex("83 3E 36 11 00 7E"), bytes.fromhex("83 3E 36 11 01 7E"))]},
        {"name": "多人競賽也可一個人玩 (光碟版 2/2)", "targets": [(bytes.fromhex("83 3E 36 11 01 75 03"), bytes.fromhex("83 06 36 11 01 EB 03"))]},
    ]

    return patch_binary(exe_target, exe_patches)

# =====================================================================
# 主幹邏輯 (獨立成一個函數讓 UI 呼叫)
# =====================================================================
def run_patch(target_dir, on_complete, on_error):
    try:
        # Step 1: 修改 EXE
        exe_res = patch_exe(target_dir, step=1)

    except Exception as e:
        err_msg = f"幹，Patch 發生嚴重錯誤：\n{str(e)}"
        emit_log(err_msg, status="FATAL")
        on_error(err_msg)
        return

    # 簡單分析成果
    report = format_report([
        ("主程式 (EXE)", exe_res),
    ])

    final_msg = f"{GAME_NAME} 全套 Patch 執行完畢！\n\n【執行摘要】\n" + report
    emit_log("所有任務完工！爽啦！", step=TOTAL_STEPS, status="DONE")

    # 回報成功
    on_complete(final_msg)

# =====================================================================
# 介面 (Rich Patch Series 共用版型)
# =====================================================================
def main():
    # 建立主視窗
    ui_root = tk.Tk()
    ui_root.title(APP_TITLE)

    # 設定視窗圖示 (icon.png)
    try:
        # 考慮到 PyInstaller 釋放路徑
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
        icon_path = os.path.join(base_path, "icon.png")
        if os.path.exists(icon_path):
            photo = tk.PhotoImage(file=icon_path)
            ui_root.iconphoto(True, photo)
    except Exception as e:
        print(f"[WARN] 載入圖示失敗，算了不影響功能: {e}")

    # 設定視窗大小與畫面置中
    window_width = 480
    window_height = 320
    screen_width = ui_root.winfo_screenwidth()
    screen_height = ui_root.winfo_screenheight()
    x_cordinate = int((screen_width / 2) - (window_width / 2))
    y_cordinate = int((screen_height / 2) - (window_height / 2))
    ui_root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")

    # 禁止縮放
    ui_root.resizable(False, False)

    # 選擇目錄區塊
    top_frame = tk.Frame(ui_root)
    top_frame.pack(padx=15, pady=(15, 0), fill=tk.X)

    dir_var = tk.StringVar(value=os.getcwd())
    tk.Label(top_frame, text="遊戲目錄:").pack(side=tk.LEFT)
    tk.Entry(top_frame, textvariable=dir_var, state='readonly', width=32).pack(side=tk.LEFT, padx=5)

    def choose_dir():
        from tkinter import filedialog
        d = filedialog.askdirectory(initialdir=dir_var.get())
        if d:
            dir_var.set(d)

    tk.Button(top_frame, text="瀏覽...", command=choose_dir).pack(side=tk.LEFT)

    start_btn = tk.Button(top_frame, text="開始", command=lambda: start_patch())
    start_btn.pack(side=tk.RIGHT)

    # 進度條
    ui_progress = ttk.Progressbar(ui_root, orient="horizontal", length=380, mode="determinate")
    ui_progress.pack(pady=(15, 10))

    # 建立滾動文字框的 Frame
    log_frame = tk.Frame(ui_root)
    log_frame.pack(padx=15, pady=(0, 15), fill=tk.BOTH, expand=True)

    # 卷軸與 Text 元件
    scrollbar = ttk.Scrollbar(log_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    ui_log_text = tk.Text(log_frame, font=("微軟正黑體", 10), yscrollcommand=scrollbar.set, state=tk.DISABLED, bg="#F0F0F0")
    ui_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=ui_log_text.yview)

    # 定義回呼函數，達成介面與邏輯解耦
    def handle_log(msg, status):
        ui_log_text.config(state=tk.NORMAL)
        ui_log_text.insert(tk.END, f"[{status}] {msg}\n")
        ui_log_text.see(tk.END)
        ui_log_text.config(state=tk.DISABLED)
        ui_root.update()

    def handle_progress(step, total):
        ui_progress['value'] = (step / total) * 100
        ui_root.update()

    def handle_complete(msg):
        ui_root.destroy()
        messagebox.showinfo(f"{GAME_NAME} 更新結果", msg)

    def handle_error(err_msg):
        ui_root.destroy()
        messagebox.showerror(f"{GAME_NAME} 更新失敗", err_msg)
        sys.exit(1)

    set_callbacks(handle_log, handle_progress)

    def start_patch():
        target_dir = dir_var.get()
        if not os.path.isdir(target_dir):
            messagebox.showwarning(APP_TITLE, "這個遊戲目錄不存在，先按「瀏覽...」重新選一個吧。")
            return

        start_btn.config(state=tk.DISABLED)
        ui_log_text.config(state=tk.NORMAL)
        ui_log_text.delete(1.0, tk.END)
        ui_log_text.config(state=tk.DISABLED)
        emit_log(f"目標目錄：{target_dir}")
        run_patch(target_dir, handle_complete, handle_error)

    # 啟動 UI 迴圈
    ui_root.mainloop()

if __name__ == "__main__":
    main()
