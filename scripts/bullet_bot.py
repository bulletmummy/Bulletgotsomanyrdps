import os, time, requests, subprocess, json, base64, threading, re
from pathlib import Path
from datetime import datetime

TOKEN       = os.environ["TG_BOT_TOKEN"]
OWNER_ID    = str(os.environ["TG_CHAT_ID"])
ALLOWED_IDS = set(os.environ.get("ALLOWED_USERS", OWNER_ID).replace(" ","").split(","))
NGROK_TOKEN = os.environ["NGROK_SHAHZAIB"]
API         = f"https://api.telegram.org/bot{TOKEN}"
GH_PAT      = os.environ.get("SECRET_SHAHZAIB","")
REPO        = os.environ.get("REPO","")

UPLOAD_DIR  = Path(r"C:\Users\Public\uploads")
IG_DIR      = Path(r"C:\Users\Public\ig_sessions")
NGROK_BIN   = Path(r"C:\Windows\Temp\ngrok\ngrok.exe")
CHROME_EXE  = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

rdp_registry  = {}
rdp_counter   = [0]
user_sessions = {}

# ── NETWORK ────────────────────────────────────────────────────────────────

def send(chat_id, text, markup=None):
    p = {"chat_id": chat_id, "text": text[:4096], "parse_mode": "Markdown"}
    if markup: p["reply_markup"] = json.dumps(markup)
    try: requests.post(f"{API}/sendMessage", json=p, timeout=10)
    except: pass

def answer_cb(cb_id):
    try: requests.post(f"{API}/answerCallbackQuery",
            json={"callback_query_id": cb_id}, timeout=5)
    except: pass

def get_updates(offset=0):
    try:
        r = requests.get(f"{API}/getUpdates",
            params={"offset": offset, "timeout": 30}, timeout=35)
        return r.json().get("result", [])
    except: return []

def is_allowed(uid): return str(uid) in ALLOWED_IDS

# ── MENU ───────────────────────────────────────────────────────────────────

def send_menu(chat_id, user_id):
    owner = str(user_id) == OWNER_ID
    btns  = [
        [{"text":"🖥️ List RDPs",     "callback_data":"list_rdp"},
         {"text":"➕ New RDP",       "callback_data":"new_rdp"}],
        [{"text":"🛑 Stop RDP",      "callback_data":"stop_one_prompt"},
         {"text":"💥 Stop ALL",      "callback_data":"stop_all"}],
        [{"text":"📤 Upload File",   "callback_data":"upload_info"},
         {"text":"📁 My Files",      "callback_data":"my_files"}],
        [{"text":"📱 IG Session",    "callback_data":"ig_menu"},
         {"text":"📊 Status",        "callback_data":"status"}],
        [{"text":"💻 Shell",         "callback_data":"shell_prompt"}],
    ]
    if owner:
        btns += [
            [{"text":"👥 Add User",  "callback_data":"add_user"},
             {"text":"🚫 Remove",    "callback_data":"remove_user"}],
            [{"text":"📋 Users",     "callback_data":"list_users"}],
        ]
    send(chat_id, "🔫 *BULLET BOT*\n\nChoose:", {"inline_keyboard": btns})

def send_ig_menu(chat_id):
    btns = [
        [{"text":"🍪 Set Session Cookie",  "callback_data":"ig_set_cookie"}],
        [{"text":"📋 Set Session JSON",    "callback_data":"ig_set_json"}],
        [{"text":"🔗 Open IG in Chrome",   "callback_data":"ig_open_chrome"}],
        [{"text":"📂 Load Session",        "callback_data":"ig_load"}],
        [{"text":"❌ Logout / Clear",      "callback_data":"ig_clear"}],
    ]
    send(chat_id,
        "📱 *Instagram Session Manager*\n\n"
        "Choose how to connect IG:",
        {"inline_keyboard": btns})

# ── RDP ────────────────────────────────────────────────────────────────────

def spawn_rdp(chat_id):
    rdp_counter[0] += 1
    slot     = rdp_counter[0]
    rdp_user = f"bulletrdp{slot}"
    rdp_pass = f"Bullet{slot}@6767"
    api_port = 4040 + slot - 1

    send(chat_id, f"⏳ Spawning RDP `#{slot}` — ~15 sec...")

    try:
        subprocess.run(f"net user {rdp_user} {rdp_pass} /add", shell=True, capture_output=True)
        subprocess.run(f"net localgroup administrators {rdp_user} /add", shell=True, capture_output=True)

        log_f = f"C:\\Windows\\Temp\\ngrok_rdp{slot}.log"
        proc  = subprocess.Popen(
            f'"{NGROK_BIN}" tcp 3389 --log=stdout --web-addr=localhost:{api_port}',
            shell=True,
            stdout=open(log_f,"w"),
            stderr=subprocess.STDOUT
        )

        time.sleep(8)
        tunnel = ""
        for _ in range(15):
            try:
                res    = requests.get(f"http://localhost:{api_port}/api/tunnels", timeout=3)
                tuns   = res.json().get("tunnels",[])
                if tuns:
                    tunnel = tuns[0]["public_url"]
                    break
            except: pass
            time.sleep(2)

        if not tunnel:
            send(chat_id, f"❌ RDP `#{slot}` tunnel failed — check ngrok token.")
            return

        hp       = tunnel.replace("tcp://","").split(":")
        rdp_host = hp[0]
        rdp_port = hp[1]

        rdp_registry[slot] = {
            "host": rdp_host, "port": rdp_port,
            "user": rdp_user, "password": rdp_pass,
            "proc": proc, "api_port": api_port,
            "created_at": datetime.utcnow().strftime("%H:%M:%S UTC")
        }

        send(chat_id,
            f"✅ *RDP #{slot} LIVE*\n\n"
            f"🖥️ Host: `{rdp_host}`\n"
            f"🔌 Port: `{rdp_port}`\n"
            f"👤 User: `{rdp_user}`\n"
            f"🔑 Pass: `{rdp_pass}`\n"
            f"⏰ {rdp_registry[slot]['created_at']}\n\n"
            f"_Chrome + Automa auto-launch on login._\n"
            f"_Other RDPs untouched._")

    except Exception as ex:
        send(chat_id, f"❌ Spawn error: `{ex}`")

def kill_rdp(slot, chat_id):
    if slot not in rdp_registry:
        send(chat_id, f"❌ RDP `#{slot}` not found. Active: `{list(rdp_registry.keys())}`")
        return
    info = rdp_registry[slot]
    try:
        p = info.get("proc")
        if p:
            p.terminate()
            try: p.wait(timeout=5)
            except: p.kill()
        subprocess.run(f"net user {info['user']} /delete", shell=True, capture_output=True)
        del rdp_registry[slot]
        remaining = list(rdp_registry.keys())
        send(chat_id,
            f"✅ RDP `#{slot}` stopped.\n"
            f"Still running: `{remaining if remaining else 'none'}`")
    except Exception as ex:
        send(chat_id, f"❌ Error: `{ex}`")

def kill_all(chat_id):
    if not rdp_registry:
        send(chat_id, "ℹ️ No active RDPs."); return
    ids = list(rdp_registry.keys())
    for slot in ids:
        try:
            p = rdp_registry[slot].get("proc")
            if p:
                p.terminate()
                try: p.wait(timeout=3)
                except: p.kill()
            subprocess.run(f"net user {rdp_registry[slot]['user']} /delete",
                shell=True, capture_output=True)
        except: pass
    rdp_registry.clear()
    send(chat_id, f"💥 All RDPs stopped: `{ids}`")

def list_rdp(chat_id):
    if not rdp_registry:
        send(chat_id, "ℹ️ No active RDPs."); return
    lines = ["🖥️ *Active RDPs:*\n"]
    for slot, info in rdp_registry.items():
        lines.append(
            f"*#{slot}* `{info['host']}:{info['port']}`\n"
            f"  👤 `{info['user']}` 🔑 `{info['password']}`\n"
            f"  ⏰ {info['created_at']}\n")
    send(chat_id, "\n".join(lines))

# ── FILE UPLOAD ────────────────────────────────────────────────────────────

def download_tg_file(file_id, save_name, user_id, chat_id):
    try:
        send(chat_id, f"📥 Downloading `{save_name}`...")
        r    = requests.get(f"{API}/getFile", params={"file_id": file_id}, timeout=10)
        fpath = r.json()["result"]["file_path"]
        url  = f"https://api.telegram.org/file/bot{TOKEN}/{fpath}"
        data = requests.get(url, timeout=120, stream=True)

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        save_path = UPLOAD_DIR / f"{user_id}_{save_name}"
        with open(save_path, "wb") as f:
            for chunk in data.iter_content(65536):
                f.write(chunk)

        size_kb = save_path.stat().st_size // 1024
        send(chat_id,
            f"✅ *File saved!*\n\n"
            f"📄 Name: `{save_name}`\n"
            f"💾 Path: `{save_path}`\n"
            f"📦 Size: `{size_kb} KB`\n\n"
            f"Use `/shell` to run or move it.")
    except Exception as ex:
        send(chat_id, f"❌ Upload failed: `{ex}`")

# ── IG SESSION ─────────────────────────────────────────────────────────────

def save_ig_session(user_id, data_str, chat_id, mode="json"):
    IG_DIR.mkdir(parents=True, exist_ok=True)

    if mode == "cookie":
        match = re.search(r"sessionid=([^;]+)", data_str)
        sid   = match.group(1) if match else data_str.strip()
        path  = IG_DIR / f"{user_id}_session.cookie"
        path.write_text(sid)

        json_path = IG_DIR / f"{user_id}_session.json"
        json_path.write_text(json.dumps({"sessionid": sid}))

        send(chat_id,
            f"✅ *IG Session Cookie Saved*\n\n"
            f"Session ID: `{sid[:20]}...`\n"
            f"Cookie: `{path}`\n"
            f"JSON: `{json_path}`\n\n"
            f"Open IG in Chrome → tap *IG → Open Chrome* button.")
    else:
        path = IG_DIR / f"{user_id}_session.json"
        path.write_text(data_str.strip())
        send(chat_id,
            f"✅ *IG Session JSON Saved*\n\n"
            f"Path: `{path}`\n\n"
            f"Load in script:\n"
            f"```python\ncl.load_settings(r'{path}')\n```")

def open_ig_chrome(chat_id, user_id):
    cookie_f = IG_DIR / f"{user_id}_session.cookie"

    if Path(CHROME_EXE).exists():
        if cookie_f.exists():
            sid = cookie_f.read_text().strip()
            subprocess.Popen(
                f'"{CHROME_EXE}" '
                f'--remote-debugging-port=9222 '
                f'--start-maximized '
                f'https://www.instagram.com',
                shell=True
            )
            time.sleep(3)

            try:
                targets = requests.get("http://localhost:9222/json", timeout=5).json()
                ws_id   = targets[0]["id"] if targets else None
                if ws_id:
                    inj_url = f"http://localhost:9222/json/activate/{ws_id}"
                    requests.get(inj_url, timeout=3)

                helper = (
                    f'document.cookie = "sessionid={sid}; '
                    f'domain=.instagram.com; path=/";'
                    f'window.location.reload();'
                )
                helper_path = "C:\\Users\\Public\\ig_cookie_inject.js"
                with open(helper_path, "w") as f:
                    f.write(helper)

                send(chat_id,
                    f"✅ Chrome opened on IG.\n\n"
                    f"If not auto-logged in, open DevTools Console and paste:\n"
                    f"```javascript\n{helper[:200]}...\n```\n"
                    f"Full script: `{helper_path}`")
            except Exception as ex:
                send(chat_id, f"⚠️ Chrome opened. Cookie inject fallback: `{ex}`")
        else:
            subprocess.Popen(
                f'"{CHROME_EXE}" --start-maximized https://www.instagram.com',
                shell=True)
            send(chat_id, "✅ Chrome opened on IG.\n\nNo session found — set one first.")
    else:
        send(chat_id, "❌ Chrome not found.")

def load_ig_session(user_id, chat_id):
    json_f   = IG_DIR / f"{user_id}_session.json"
    cookie_f = IG_DIR / f"{user_id}_session.cookie"
    if json_f.exists():
        data = json_f.read_text()[:500]
        send(chat_id, f"📋 *Your IG Session JSON:*\n```json\n{data}\n```")
    elif cookie_f.exists():
        sid = cookie_f.read_text().strip()
        send(chat_id, f"🍪 *Your Session ID:*\n`{sid}`")
    else:
        send(chat_id, "⚠️ No IG session saved yet.")

def clear_ig_session(user_id, chat_id):
    for f in [IG_DIR / f"{user_id}_session.json",
              IG_DIR / f"{user_id}_session.cookie"]:
        if f.exists(): f.unlink()
    send(chat_id, "✅ IG session cleared.")

# ── TEXT HANDLER ───────────────────────────────────────────────────────────

def handle_text(user_id, chat_id, text):
    st  = user_sessions.setdefault(str(user_id), {})
    aw  = st.get("awaiting")

    if aw == "shell":
        st["awaiting"] = None
        try:
            out = subprocess.check_output(
                text, shell=True, stderr=subprocess.STDOUT, timeout=25
            ).decode(errors="replace")
            send(chat_id, f"```\n{out[:3500]}\n```")
        except subprocess.CalledProcessError as e:
            send(chat_id, f"❌ ```\n{e.output.decode(errors='replace')[:2000]}\n```")
        return

    elif aw == "stop_one":
        st["awaiting"] = None
        try: kill_rdp(int(text.strip()), chat_id)
        except: send(chat_id, "❌ Send a valid number e.g. `1`")
        return

    elif aw == "ig_set_cookie":
        st["awaiting"] = None
        save_ig_session(str(user_id), text, chat_id, mode="cookie")
        return

    elif aw == "ig_set_json":
        st["awaiting"] = None
        save_ig_session(str(user_id), text, chat_id, mode="json")
        return

    elif aw == "add_user":
        st["awaiting"] = None
        ALLOWED_IDS.add(text.strip())
        send(chat_id, f"✅ Added `{text.strip()}`")
        return

    elif aw == "remove_user":
        st["awaiting"] = None
        ALLOWED_IDS.discard(text.strip())
        send(chat_id, f"✅ Removed `{text.strip()}`")
        return

    t = text.strip().lower()

    if t in ["/start","/menu","/help"]:
        send_menu(chat_id, user_id)
    elif t == "/newrdp":
        threading.Thread(target=spawn_rdp, args=(chat_id,), daemon=True).start()
    elif t == "/listrdp":
        list_rdp(chat_id)
    elif t == "/stopall":
        kill_all(chat_id)
    elif t.startswith("/stop "):
        try: kill_rdp(int(t.split()[1]), chat_id)
        except: send(chat_id, "Usage: `/stop 1`")
    elif t == "/upload":
        send(chat_id,
            "📤 *Upload File*\n\n"
            "Just send any file directly to this chat.\n"
            "It saves to `C:\\Users\\Public\\uploads\\`")
    elif t == "/shell":
        st["awaiting"] = "shell"
        send(chat_id, "💻 Send command:")
    elif t == "/ig":
        send_ig_menu(chat_id)
    elif t == "/status":
        handle_cb(user_id, chat_id, "status", "0")
    else:
        send(chat_id, "❓ Unknown. Send `/menu`")

# ── CALLBACK HANDLER ───────────────────────────────────────────────────────

def handle_cb(user_id, chat_id, data, cb_id):
    answer_cb(cb_id)
    st    = user_sessions.setdefault(str(user_id), {})
    owner = str(user_id) == OWNER_ID

    if data == "list_rdp":          list_rdp(chat_id)
    elif data == "new_rdp":         threading.Thread(target=spawn_rdp, args=(chat_id,), daemon=True).start()
    elif data == "stop_all":        kill_all(chat_id)
    elif data == "stop_one_prompt":
        st["awaiting"] = "stop_one"
        send(chat_id, f"🛑 Active: `{list(rdp_registry.keys())}`\n\nSend RDP number to stop:")
    elif data == "upload_info":
        send(chat_id,
            "📤 *Upload File*\n\n"
            "Just send any file to this chat — doc, photo, video, zip, anything.\n"
            "Auto-saved to `C:\\Users\\Public\\uploads\\`")
    elif data == "my_files":
        files = list(UPLOAD_DIR.glob(f"{user_id}_*")) if UPLOAD_DIR.exists() else []
        if files:
            lines = ["📁 *Your Files:*\n"]
            for f in files[:20]:
                kb = f.stat().st_size // 1024
                lines.append(f"`{f.name}` ({kb} KB)")
            send(chat_id, "\n".join(lines))
        else:
            send(chat_id, "📁 No files uploaded yet.")
    elif data == "ig_menu":         send_ig_menu(chat_id)
    elif data == "ig_set_cookie":
        st["awaiting"] = "ig_set_cookie"
        send(chat_id,
            "🍪 *Set IG Session Cookie*\n\n"
            "Paste your `sessionid` value here.\n\n"
            "How to get it:\n"
            "1. Open Instagram in Chrome\n"
            "2. F12 → Application → Cookies → `https://www.instagram.com`\n"
            "3. Copy value of `sessionid`\n\n"
            "Paste it now:")
    elif data == "ig_set_json":
        st["awaiting"] = "ig_set_json"
        send(chat_id,
            "📋 *Set IG Session JSON*\n\n"
            "Paste your instagrapi `settings.json` content here:")
    elif data == "ig_open_chrome":
        threading.Thread(
            target=open_ig_chrome, args=(chat_id, str(user_id)), daemon=True
        ).start()
    elif data == "ig_load":         load_ig_session(str(user_id), chat_id)
    elif data == "ig_clear":        clear_ig_session(str(user_id), chat_id)
    elif data == "status":
        try:
            import psutil
            cpu  = psutil.cpu_percent(interval=1)
            ram  = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")
            send(chat_id,
                f"⚙️ *Status*\n"
                f"CPU:  `{cpu}%`\n"
                f"RAM:  `{ram.used/1e9:.1f}/{ram.total/1e9:.1f} GB ({ram.percent}%)`\n"
                f"Disk: `{disk.used/1e9:.1f}/{disk.total/1e9:.1f} GB`\n"
                f"RDPs: `{len(rdp_registry)} active`")
        except: send(chat_id, "⚠️ psutil issue")
    elif data == "shell_prompt":
        st["awaiting"] = "shell"
        send(chat_id, "💻 Send command:")
    elif data == "add_user":
        if not owner: send(chat_id, "❌ Owner only."); return
        st["awaiting"] = "add_user"
        send(chat_id, "👤 Send TG user ID to add:")
    elif data == "remove_user":
        if not owner: send(chat_id, "❌ Owner only."); return
        st["awaiting"] = "remove_user"
        send(chat_id, "🚫 Send TG user ID to remove:")
    elif data == "list_users":
        if not owner: send(chat_id, "❌ Owner only."); return
        send(chat_id, "👥 *Allowed Users:*\n" + "\n".join([f"`{u}`" for u in ALLOWED_IDS]))

# ── FILE/MEDIA HANDLER ─────────────────────────────────────────────────────

def handle_media(user_id, chat_id, msg):
    if "document" in msg:
        doc  = msg["document"]
        name = doc.get("file_name", f"doc_{int(time.time())}")
        threading.Thread(target=download_tg_file,
            args=(doc["file_id"], name, str(user_id), chat_id), daemon=True).start()
    elif "photo" in msg:
        photo = msg["photo"][-1]
        name  = f"photo_{int(time.time())}.jpg"
        threading.Thread(target=download_tg_file,
            args=(photo["file_id"], name, str(user_id), chat_id), daemon=True).start()
    elif "video" in msg:
        vid  = msg["video"]
        name = vid.get("file_name", f"video_{int(time.time())}.mp4")
        threading.Thread(target=download_tg_file,
            args=(vid["file_id"], name, str(user_id), chat_id), daemon=True).start()
    elif "audio" in msg:
        aud  = msg["audio"]
        name = aud.get("file_name", f"audio_{int(time.time())}.mp3")
        threading.Thread(target=download_tg_file,
            args=(aud["file_id"], name, str(user_id), chat_id), daemon=True).start()
    elif "voice" in msg:
        threading.Thread(target=download_tg_file,
            args=(msg["voice"]["file_id"], f"voice_{int(time.time())}.ogg",
                  str(user_id), chat_id), daemon=True).start()

# ── BOOT ───────────────────────────────────────────────────────────────────

send(OWNER_ID,
    "🔫 *BULLET BOT ONLINE*\n\n"
    "`/newrdp` — spawn RDP (Chrome auto-opens IG on login)\n"
    "`/stop 1` — stop RDP #1 only\n"
    "`/stopall` — kill all RDPs\n"
    "`/listrdp` — all active RDPs\n"
    "`/upload` OR just send any file\n"
    "`/ig` — Instagram session manager\n"
    "`/shell` — run command\n"
    "`/status` — system stats\n"
    "`/menu` — button menu")

offset = 0
while True:
    updates = get_updates(offset)
    for u in updates:
        offset = u["update_id"] + 1

        if "callback_query" in u:
            cq    = u["callback_query"]
            uid   = str(cq["from"]["id"])
            cid   = str(cq["message"]["chat"]["id"])
            data  = cq.get("data","")
            cb_id = cq["id"]
            if not is_allowed(uid):
                send(cid, f"❌ Access denied. Your ID: `{uid}`")
                answer_cb(cb_id); continue
            handle_cb(uid, cid, data, cb_id)
            continue

        msg = u.get("message",{})
        if not msg: continue
        uid = str(msg.get("from",{}).get("id",""))
        cid = str(msg.get("chat",{}).get("id",""))
        if not uid: continue

        if not is_allowed(uid):
            send(cid, f"❌ Access denied.\nYour TG ID: `{uid}`"); continue

        if any(k in msg for k in ["document","photo","video","audio","voice"]):
            handle_media(uid, cid, msg)
            continue

        text = msg.get("text","")
        if text:
            handle_text(uid, cid, text)

    time.sleep(1)
