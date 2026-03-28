import tkinter as tk
from tkinter import ttk
import os
import sys
import shutil
import ctypes

try:
    from PIL import Image
except ImportError:
    print("[ERROR][INIT] 雞歪，少了 PIL 套件！請執行 pip install Pillow")
    sys.exit(1)

# =====================================================================
# 全域 UI 變數與 Log 系統
# =====================================================================
ui_root = None
ui_log_text = None
ui_progress = None

TOTAL_STEPS = 1

def emit_log(msg, step=None, status="INFO"):
    """
    更新終端機輸出，並同步更新 tkinter 介面的進度與文字
    """
    step_tag = f"[STEP {step}/{TOTAL_STEPS}]" if step else "[DETAILS]"
    print(f"[{status}]{step_tag} {msg}", flush=True)

    if ui_root and ui_log_text:
        ui_log_text.config(state=tk.NORMAL)
        ui_log_text.insert(tk.END, f"[{status}] {msg}\n")
        ui_log_text.see(tk.END)
        ui_log_text.config(state=tk.DISABLED)
        if step:
            ui_progress['value'] = (step / TOTAL_STEPS) * 100
        ui_root.update()

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

def patch_binary(filename, patches):
    with open(filename, "rb") as f:
        data = f.read()
        
    emit_log(f"開始分析與 Patch {filename} ...")
    modified_data = data
    success_count = 0
    
    for patch in patches:
        name = patch['name']
        success = False
        
        for target, replacement in patch['targets']:
            if target in modified_data:
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

# =====================================================================
# 核心處理函數
# =====================================================================
def patch_exe(step):
    emit_log("開始尋找主程式並進行修改...", step=step)
    # 改抓大富翁2的主程式 RUN.EXE
    exe_target = next((name for name in ["RUN.EXE", "run.exe"] if os.path.exists(name)), None)
            
    if not exe_target:
        emit_log("靠背，找不到 RUN.EXE！請確認檔案在同目錄。", status="ERROR")
        return False
        
    emit_log(f"找到主程式：{exe_target}")
    backup_file(exe_target)
    
    # 將你提供的磁片版與光碟版特徵碼放入
    exe_patches = [
        # 磁片版
        {"name": "多人模式可單獨一人玩 (磁片版 1/2)", "targets": [(bytes.fromhex("83 3E E8 10 00 7E"), bytes.fromhex("83 3E E8 10 01 7E"))]},
        {"name": "多人模式可單獨一人玩 (磁片版 2/2)", "targets": [(bytes.fromhex("83 3E E8 10 01 75 03"), bytes.fromhex("83 06 E8 10 01 EB 03"))]},
        # 光碟典藏版
        {"name": "多人模式可單獨一人玩 (光碟版 1/2)", "targets": [(bytes.fromhex("83 3E 36 11 00 7E"), bytes.fromhex("83 3E 36 11 01 7E"))]},
        {"name": "多人模式可單獨一人玩 (光碟版 2/2)", "targets": [(bytes.fromhex("83 3E 36 11 01 75 03"), bytes.fromhex("83 06 36 11 01 EB 03"))]},
    ]
    
    return patch_binary(exe_target, exe_patches)

# =====================================================================
# 主幹邏輯
# =====================================================================
def run_patch():
    try:
        # 只需要執行修改 EXE 這一步
        exe_res = patch_exe(step=1)
        
    except Exception as e:
        err_msg = f"幹，Patch 發生嚴重錯誤：\n{str(e)}"
        emit_log(err_msg, status="FATAL")
        if ui_root:
            ui_root.destroy()
        ctypes.windll.user32.MessageBoxW(0, err_msg, "大富翁2 更新失敗", 0)
        sys.exit(1)

    # 簡單分析成果
    report = []
    report.append("✅ 主程式 (EXE): 成功處理" if exe_res else "⚠️ 主程式 (EXE): 未變動或失敗")

    final_msg = "大富翁2 Patch 執行完畢！\n\n【執行摘要】\n" + "\n".join(report)
    emit_log("任務完工！爽啦！", step=TOTAL_STEPS, status="DONE")
    
    # 關閉進度條視窗，彈出最終結果
    if ui_root:
        ui_root.destroy()
    ctypes.windll.user32.MessageBoxW(0, final_msg, "大富翁2 更新結果", 0)

def main():
    global ui_root, ui_progress
    
    ui_root = tk.Tk()
    ui_root.title("大富翁2 Patch")
    
    try:
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
        icon_path = os.path.join(base_path, "icon.png")
        if os.path.exists(icon_path):
            img = Image.open(icon_path)
            photo = tk.PhotoImage(file=icon_path)
            ui_root.iconphoto(True, photo)
    except Exception as e:
        pass

    window_width = 480
    window_height = 280
    screen_width = ui_root.winfo_screenwidth()
    screen_height = ui_root.winfo_screenheight()
    x_cordinate = int((screen_width/2) - (window_width/2))
    y_cordinate = int((screen_height/2) - (window_height/2))
    ui_root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
    
    ui_root.resizable(False, False)

    ui_progress = ttk.Progressbar(ui_root, orient="horizontal", length=380, mode="determinate")
    ui_progress.pack(pady=(15, 10))

    log_frame = tk.Frame(ui_root)
    log_frame.pack(padx=15, pady=(0, 15), fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(log_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    global ui_log_text
    ui_log_text = tk.Text(log_frame, font=("微軟正黑體"), yscrollcommand=scrollbar.set, state=tk.DISABLED, bg="#F0F0F0")
    ui_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=ui_log_text.yview)

    ui_root.after(500, run_patch)
    ui_root.mainloop()

if __name__ == "__main__":
    main()