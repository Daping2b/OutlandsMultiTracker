"""
Outlands Multi Tracker
By Daping — Windows
"""
import threading
import sys, json, re, csv, threading
from datetime import datetime, timedelta, date
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

try:
    from tkcalendar import DateEntry
    HAS_CAL = True
except ImportError:
    HAS_CAL = False

import urllib.request, urllib.error, zipfile, shutil, subprocess, os

GITHUB_USER    = "Daping2b"
GITHUB_REPO    = "OutlandsMultiTracker"
GITHUB_API     = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

# ── Paths ──────────────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

CONFIG_DIR  = BASE_DIR / "config"
DATA_DIR    = BASE_DIR / "data"
ASSETS_DIR  = BASE_DIR / "assets"
SCRIPTS_DIR = BASE_DIR / "scripts"
DATA_DIR.mkdir(exist_ok=True)

def _ap(name): return str((ASSETS_DIR / name).resolve())

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except: return default if default is not None else {}

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[SAVE] Failed to save {path}: {e}")

VER_DATA    = load_json(CONFIG_DIR/"version.json", {"version":"0.0","app_name":"Outlands Multi Tracker"})
APP_VERSION = VER_DATA.get("version","0.3")
APP_NAME    = VER_DATA.get("app_name","Outlands Multi Tracker")
SETTINGS_F  = CONFIG_DIR / "settings.json"
SESSIONS_F  = DATA_DIR   / "sessions.json"
XP_F        = DATA_DIR   / "xp_data.json"

# ── Palette + utilitaires partagés ─────────────────────────────────────────────
# Source unique dans ui_helpers.py — ne pas dupliquer ici
from ui_helpers import *
# Fonctions privées (préfixe _) non exportées par import * — import explicite
from ui_helpers import _expand_abbrev, _clean_item_name, _ap



# ── Update progress modal ─────────────────────────────────────────────────────
# UpdateModal replaced by floating update panel (_show_update_panel in App)

# ── Loading modal ──────────────────────────────────────────────────────────────
class LoadingModal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Loading logs...")
        self.configure(bg=BG); self.resizable(False,False)
        self.grab_set(); self.protocol("WM_DELETE_WINDOW", lambda: None)
        w,h=480,160
        px=parent.winfo_x()+parent.winfo_width()//2-w//2
        py=parent.winfo_y()+parent.winfo_height()//2-h//2
        self.geometry(f"{w}x{h}+{px}+{py}")
        # Appliquer icône OMT après initialisation
        try:
            ico = str(ASSETS_DIR / "O-MTSmall.ico")
            self.after(250, lambda: self.iconbitmap(ico) if self.winfo_exists() else None)
        except Exception:
            pass
        border=tk.Frame(self,bg=GOLD,bd=2); border.pack(fill="both",expand=True,padx=2,pady=2)
        inner=tk.Frame(border,bg=BG); inner.pack(fill="both",expand=True)
        tk.Label(inner,text="Loading Logs",bg=BG,fg=GOLD_LT,font=("Georgia",15,"bold")).pack(pady=(18,4))
        self._file_lbl=tk.Label(inner,text="Initializing...",bg=BG,fg=DIM2,font=("Segoe UI",11)); self._file_lbl.pack(pady=2)
        self._pct_lbl=tk.Label(inner,text="0 / 0",bg=BG,fg=TEXT,font=("Segoe UI",11)); self._pct_lbl.pack(pady=0)
        bar_frame=tk.Frame(inner,bg=BG4,height=14,width=420); bar_frame.pack(pady=10,padx=20); bar_frame.pack_propagate(False)
        self._fill=tk.Frame(bar_frame,bg=GOLD,height=14); self._fill.place(x=0,y=0,relheight=1,width=0); self._bar_w=420

    def update_progress(self, done, total, fname=""):
        pct=done/max(1,total); fw=int(self._bar_w*pct)
        self._fill.place(x=0,y=0,relheight=1,width=fw)
        self._file_lbl.configure(text=fname[:60])
        self._pct_lbl.configure(text=f"{done} / {total}  ({int(pct*100)}%)")
        self.update_idletasks()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════
from log_analysis   import LogMixin
import crash_reporter
from experience     import ExperienceMixin
from guild_core     import GuildCoreMixin
from guild_members  import GuildMembersMixin
from guild_bot      import GuildBotMixin
from guild_login    import GuildLoginMixin
from guild_admin    import GuildAdminMixin
from guild_sessions import GuildSessionsMixin
from guild_uploads  import GuildUploadsMixin
from loading_modal  import LoadingModal as _LoadingModal

class App(LogMixin, ExperienceMixin, GuildCoreMixin, GuildMembersMixin,
          GuildBotMixin, GuildLoginMixin, GuildAdminMixin,
          GuildSessionsMixin, GuildUploadsMixin, ctk.CTk):
              
    def __init__(self):
        super().__init__()
        self.settings  = load_json(SETTINGS_F, {"uo_root_path":""})
        self.sess_db   = load_json(SESSIONS_F, {"known_files":[],"sessions":[]})
        self.xp_db     = load_json(XP_F,       {"events":[]})
        self.dung_data = load_json(CONFIG_DIR/"Dungeon.json",    {"dungeons":[]})
        self.wild_data = load_json(CONFIG_DIR/"Wilderness.json", {"wilderness":[]})
        self.howto     = load_json(CONFIG_DIR/"howto_content.json", {"sections":[],"special_thanks":{}})
        self.bonuses_db = load_json(CONFIG_DIR/"bonuses.json",    {})
        self.sessions  = self._de_sess(self.sess_db.get("sessions",[]))
        self.xp_events = self._de_xp(self.xp_db.get("events",[]))
        self._sel       = {}
        self._act_f     = "All"
        self._char_f    = "All"
        self._photos    = []
        self._sort_col  = "date"
        self._sort_rev  = True
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        if not self.settings.get("uo_root_path"):
            self.after(800, self._first_run)
        # Check for updates — skip if just updated (flag file present)
        _flag = BASE_DIR / "_just_updated"
        try:
            if _flag.exists(): _flag.unlink()
        except: pass
        # Always check for update at startup
        threading.Thread(target=self._check_update, daemon=True).start()
        threading.Thread(target=self._fetch_bonuses, daemon=True).start()
    # ── Serialise ──────────────────────────────────────────────────────────────
    def _ser_sess(self,ss):
        out=[]
        for s in ss:
            d=dict(s)
            d["start"]=s["start"].isoformat() if s.get("start") else None
            d["end"]  =s["end"].isoformat()   if s.get("end")   else None
            out.append(d)
        return out
    def _de_sess(self,raw):
        out=[]
        for r in raw:
            d=dict(r)
            d["start"]=datetime.fromisoformat(r["start"]) if r.get("start") else None
            d["end"]  =datetime.fromisoformat(r["end"])   if r.get("end")   else None
            out.append(d)
        return out
    def _ser_xp(self,ev):
        return [{"ts":e["ts"].isoformat(),"player":e["player"],"aspect":e["aspect"],
                 "xp_cur":e["xp_cur"],"xp_max":e["xp_max"]} for e in ev]
    def _de_xp(self,raw):
        out=[]
        for r in raw:
            try: out.append({"ts":datetime.fromisoformat(r["ts"]),"player":r["player"],
                             "aspect":r["aspect"],"xp_cur":r["xp_cur"],"xp_max":r["xp_max"]})
            except: pass
        return out
    def _keep(self,ph):
        if ph: self._photos.append(ph)
        return ph

    # ── Auto-update ────────────────────────────────────────────────────────────
    def _check_update(self):
        """Auto-check at startup — if update found, download immediately."""
        try:
            latest, url = check_for_update()
            if latest and version_newer(latest, APP_VERSION):
                self.after(0, lambda l=latest, u=url: self._run_update(l, u))
        except Exception as e:
            print(f"[UPDATE] Check failed: {e}")

    # ── Bonuses ────────────────────────────────────────────────────────────────
    def _fetch_bonuses(self):
        """Fetch bonuses.json from GitHub API (bypasses CDN cache). Runs in daemon thread."""
        import urllib.request, urllib.error, json as _json, base64 as _b64
        api_url = (
            f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}"
            f"/contents/config/bonuses.json"
        )
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "OMT/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = _json.loads(r.read().decode())
            content = _b64.b64decode(data["content"]).decode("utf-8")
            bonuses = _json.loads(content)
            if bonuses:
                self.bonuses_db = bonuses
                save_json(CONFIG_DIR / "bonuses.json", bonuses)
                self.after(0, self._refresh_act_tree)
                print("[BONUS] Fetched from GitHub API OK")
        except Exception as e:
            print(f"[BONUS] Fetch failed: {e}")

    def _get_current_bonuses(self):
        """Return bonus dict for the current week. Supports both YYYY-WXX and YYYY-MM-DD key formats."""
        if not self.bonuses_db:
            return {}
        today = datetime.utcnow().date()
        # Try ISO week format first (legacy)
        week_key = today.strftime("%G-W%V")
        if week_key in self.bonuses_db:
            return self.bonuses_db[week_key]
        # Try YYYY-MM-DD format (new — Saturday of current week)
        days_since_sat = (today.weekday() + 2) % 7
        sat_key = (today - __import__('datetime').timedelta(days=days_since_sat)).strftime("%Y-%m-%d")
        if sat_key in self.bonuses_db:
            return self.bonuses_db[sat_key]
        # Fallback: most recent week
        try:
            latest_key = max(self.bonuses_db.keys())
            return self.bonuses_db[latest_key]
        except Exception:
            return {}

    def _get_bonus_for_session(self, s):
        """Return bonus dict for a session based on its location and week.
        Supports YYYY-WXX (legacy) and YYYY-MM-DD (new) key formats — retroactive."""
        if not self.bonuses_db:
            return None
        location = s.get("location")
        if not location:
            return None
        base = re.sub(r'\s+Lv-\d+$', '', location).strip()
        start = s.get("start")
        bonuses = None
        if start:
            try:
                import datetime as _dt
                # Try ISO week key (legacy format)
                week_key_iso = start.strftime("%G-W%V")
                if week_key_iso in self.bonuses_db:
                    bonuses = self.bonuses_db[week_key_iso]
                else:
                    # Try YYYY-MM-DD key (new format — Saturday of the session's week)
                    sd = start.date() if hasattr(start, 'date') else start
                    days_since_sat = (sd.weekday() + 2) % 7
                    sat_key = (sd - _dt.timedelta(days=days_since_sat)).strftime("%Y-%m-%d")
                    if sat_key in self.bonuses_db:
                        bonuses = self.bonuses_db[sat_key]
            except Exception:
                pass
        # Fallback: current week bonuses
        if not bonuses:
            bonuses = self._get_current_bonuses()
        if not bonuses:
            return None
        for k, v in bonuses.items():
            if _expand_abbrev(k) in _expand_abbrev(base) or _expand_abbrev(base) in _expand_abbrev(k):
                return v
        return None

    def _refresh_act_tree(self):
        """Refresh the activities tree after bonus data update."""
        try:
            self._fill_act_tree()
        except Exception:
            pass

    def _run_update(self, version, url):
        """Start background download + show floating panel. Called auto or manually."""
        # If already downloading or ready, don't restart
        if getattr(self, "_upd_running", False):
            self._show_panel()
            return
        self._upd_running = True
        self._upd_version = version
        self._upd_pre_dir = None
        # Build panel before starting thread
        self._build_update_panel(version)
        self._panel_set("Downloading...", 0)

        def _download():
            try:
                _last_ui = [0.0]
                def cb(done, total, msg):
                    import time as _t
                    now = _t.monotonic()
                    if now - _last_ui[0] < 0.15: return  # throttle: max 1 UI update per 150ms
                    _last_ui[0] = now
                    pct = done / max(1, total)
                    self.after(0, lambda p=pct, m=msg: self._panel_set(m, p))
                pre_dir = download_update(url, cb)
                self._upd_pre_dir = pre_dir
                self.after(0, self._panel_ready)
            except Exception as e:
                self._upd_running = False
                self.after(0, lambda m=str(e): self._panel_error(m))

        threading.Thread(target=_download, daemon=True).start()

    def _do_restart_and_update(self):
        """User clicked Restart — launch updater and exit."""
        try:
            launch_updater(getattr(self, "_upd_pre_dir", None))
            self.after(50, lambda: os._exit(0))
        except Exception as e:
            messagebox.showerror("Update failed", f"Could not launch updater:\n{e}")

    def _build_update_panel(self, version):
        """Build the floating panel. Destroys old one if exists."""
        # Destroy old panel cleanly
        for attr in ("_upd_panel", "_upd_mini"):
            w = getattr(self, attr, None)
            if w:
                try: w.destroy()
                except: pass
            setattr(self, attr, None)

        panel = ctk.CTkFrame(self, fg_color=BG2, border_width=1,
                             border_color=GOLD_DK, corner_radius=8, width=260)
        panel.pack_propagate(False)
        self._upd_panel = panel

        # Header
        hdr = ctk.CTkFrame(panel, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(10,4))
        ctk.CTkLabel(hdr, text=f"⬇  Update v{version}",
                     font=("Segoe UI",12,"bold"), text_color=GOLD_LT,
                     fg_color="transparent").pack(side="left")
        ctk.CTkButton(hdr, text="×", width=22, height=22, font=("Segoe UI",14),
                      fg_color="transparent", text_color=DIM2, hover_color=BG4,
                      command=self._hide_panel).pack(side="right")

        # Status
        self._upd_status = ctk.CTkLabel(panel, text="",
                                         font=("Segoe UI",11), text_color=DIM2,
                                         fg_color="transparent")
        self._upd_status.pack(padx=10, pady=(0,4))

        # Progress bar container
        bar_bg = ctk.CTkFrame(panel, fg_color=BG4, height=8, corner_radius=4)
        bar_bg.pack(fill="x", padx=10, pady=(0,4))
        bar_bg.pack_propagate(False)
        self._upd_bar_bg  = bar_bg
        self._upd_bar_fill = ctk.CTkFrame(bar_bg, fg_color=GOLD, height=8,
                                           corner_radius=4)
        self._upd_bar_fill.place(relx=0, rely=0, relheight=1, relwidth=0)

        # Pct label
        self._upd_pct = ctk.CTkLabel(panel, text="", font=("Segoe UI",10),
                                      text_color=DIM2, fg_color="transparent")
        self._upd_pct.pack(pady=(0,4))

        # Restart button — hidden until ready
        self._upd_restart = ctk.CTkButton(
            panel, text="⟳  Restart to Update", width=220, height=34,
            fg_color=GOLD, text_color="#050505", hover_color=GOLD_LT,
            font=("Segoe UI",12,"bold"), corner_radius=6,
            command=self._do_restart_and_update)

        ctk.CTkFrame(panel, fg_color="transparent", height=6).pack()

        # Mini button (hidden initially)
        self._upd_mini = ctk.CTkButton(
            self, text="⬇", width=38, height=38, font=("Segoe UI",16),
            fg_color=GOLD, text_color="#050505", hover_color=GOLD_LT,
            corner_radius=19, command=self._show_panel)

        self._show_panel()

    def _show_panel(self):
        """Place the full panel bottom-right."""
        if self._upd_panel and self._upd_panel.winfo_exists():
            if self._upd_mini and self._upd_mini.winfo_exists():
                self._upd_mini.place_forget()
            self._upd_panel.place(relx=1.0, rely=1.0, anchor="se", x=-16, y=-16)
            self._upd_panel.lift()

    def _hide_panel(self):
        """Hide panel, show mini button."""
        if self._upd_panel and self._upd_panel.winfo_exists():
            self._upd_panel.place_forget()
        if self._upd_mini and self._upd_mini.winfo_exists():
            self._upd_mini.place(relx=1.0, rely=1.0, anchor="se", x=-16, y=-16)
            self._upd_mini.lift()

    def _panel_set(self, msg, pct):
        """Update progress bar and status label."""
        try:
            self._upd_status.configure(text=msg[:45])
            self._upd_bar_fill.place(relx=0, rely=0, relheight=1, relwidth=min(1.0, pct))
            if pct > 0 and pct < 1:
                self._upd_pct.configure(text=f"{int(pct*100)}%")
            else:
                self._upd_pct.configure(text="")
        except Exception: pass

    def _panel_ready(self):
        """Show green bar + Restart button."""
        try:
            self._upd_status.configure(text="Ready to install ✓", text_color="#80c080")
            self._upd_pct.configure(text="")
            self._upd_bar_fill.configure(fg_color="#80c080")
            self._upd_bar_fill.place(relx=0, rely=0, relheight=1, relwidth=1.0)
            self._upd_restart.pack(padx=10, pady=(0,10))
            self._show_panel()
        except Exception as e:
            print(f"[UPD] panel_ready error: {e}")

    def _panel_error(self, msg):
        """Show error in panel."""
        try:
            self._upd_status.configure(text=f"⚠ {msg[:45]}", text_color="#cc4444")
            self._upd_pct.configure(text="")
        except Exception: pass

    def _open_feedback(self):
        """Show feedback modal — 4 types : Bug / Suggestion / Location / Other."""
        modal = tk.Toplevel(self)
        modal.title("Feedback")
        modal.configure(bg=BG)
        modal.resizable(False, False)
        modal.grab_set()
        modal.protocol("WM_DELETE_WINDOW", modal.destroy)
        w, h = 500, 580
        x = self.winfo_rootx() + (self.winfo_width()  - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        modal.geometry(f"{w}x{h}+{x}+{y}")
        try:
            ico = str(ASSETS_DIR / "O-MTSmall.ico")
            modal.after(250, lambda: modal.iconbitmap(ico) if modal.winfo_exists() else None)
        except Exception:
            pass

        # Header
        hdr = ctk.CTkFrame(modal, fg_color=BG2, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="\u2694  O-MT Feedback",
                     font=("Georgia", 16, "bold"), text_color=GOLD_LT,
                     fg_color=BG2).pack(pady=(14,2))
        ctk.CTkLabel(hdr, text="Report a bug, share a suggestion or a location",
                     font=F_SMALL, text_color=DIM2, fg_color=BG2).pack(pady=(0,12))
        ctk.CTkFrame(hdr, fg_color=GOLD_DK, height=1).pack(fill="x")

        scroll_frame = ctk.CTkScrollableFrame(modal, fg_color=BG, corner_radius=0)
        scroll_frame.pack(fill="both", expand=True, padx=16, pady=12)

        # Type selection — 4 boutons sur 2 lignes (2×2)
        ctk.CTkLabel(scroll_frame, text="Type", font=F_BODY, text_color=DIM2,
                     anchor="w").pack(fill="x", pady=(0,6))
        type_var = tk.StringVar(value="")
        type_grid = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        type_grid.pack(fill="x", pady=(0,4))
        type_btns = {}

        TYPES = [
            ("Bug",        "\U0001f41b", "Report a bug",          13395012),   # rouge
            ("Suggestion", "\U0001f4a1", "Share an idea",          3066993),   # vert
            ("Location",   "\U0001f4cd", "Share a map location",   3066993),   # vert
            ("Other",      "\U0001f4dd", "Anything else",          5604556),   # gris-bleu
        ]

        def select_type(t):
            type_var.set(t)
            for k, b in type_btns.items():
                b.configure(fg_color=GOLD if k==t else BG3,
                            text_color="#050505" if k==t else DIM2,
                            border_color=GOLD if k==t else BORDER)

        for idx, (label, emoji, subtitle, _color) in enumerate(TYPES):
            col = idx % 2
            row = idx // 2
            cell = ctk.CTkFrame(type_grid, fg_color="transparent")
            cell.grid(row=row, column=col, padx=(0,6) if col==0 else 0, pady=(0,6), sticky="ew")
            type_grid.columnconfigure(col, weight=1)
            b = ctk.CTkButton(cell, text=f"{emoji}  {label}", width=220, height=40,
                              fg_color=BG3, text_color=DIM2, hover_color=BG4,
                              border_width=1, border_color=BORDER, corner_radius=6,
                              font=F_BODY, command=lambda t=label: select_type(t))
            b.pack(fill="x")
            ctk.CTkLabel(cell, text=subtitle, font=F_SMALL, text_color=DIM2,
                         anchor="center", justify="center").pack(pady=(2,0))
            type_btns[label] = b

        # Description
        ctk.CTkLabel(scroll_frame, text="Description", font=F_BODY, text_color=DIM2,
                     anchor="w").pack(fill="x", pady=(8,6))
        desc_box = ctk.CTkTextbox(scroll_frame, height=100, font=F_BODY,
                                   fg_color=BG3, border_color=BORDER, border_width=1)
        desc_box.pack(fill="x", pady=(0,12))

        # Pseudo
        ctk.CTkLabel(scroll_frame, text="In-game name  (optional)", font=F_BODY,
                     text_color=DIM2, anchor="w").pack(fill="x", pady=(0,6))
        pseudo_entry = ctk.CTkEntry(scroll_frame, placeholder_text="Your character name",
                                    height=36, font=F_BODY)
        pseudo_entry.pack(fill="x", pady=(0,12))

        # Status label
        status_lbl = ctk.CTkLabel(scroll_frame, text="", font=F_SMALL,
                                   text_color=DIM2, fg_color="transparent")
        status_lbl.pack()

        def send():
            ftype   = type_var.get()
            version = APP_VERSION
            desc    = desc_box.get("1.0", "end").strip()
            pseudo  = pseudo_entry.get().strip() or "Anonymous"
            if not ftype: status_lbl.configure(text="\u26a0 Please select a type.", text_color="#cc4444"); return
            if not desc:  status_lbl.configure(text="\u26a0 Please add a description.", text_color="#cc4444"); return

            send_btn.configure(state="disabled", text="Sending...")
            status_lbl.configure(text="", text_color=DIM2)

            type_data = {t[0]: (t[1], t[3]) for t in TYPES}
            emoji, color = type_data.get(ftype, ("\U0001f4dd", 5604556))

            import urllib.request as _ur, json as _json, ssl as _ssl
            payload = _json.dumps({"embeds":[{
                "title": f"{emoji}  New Feedback — {ftype}",
                "description": desc,
                "color": color,
                "fields": [
                    {"name":"Version","value":version,"inline":True},
                    {"name":"Type",   "value":ftype,  "inline":True},
                    {"name":"Player", "value":pseudo, "inline":True}
                ],
                "footer":{"text":f"OMT Feedback \u2022 {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}"}
            }]}).encode()

            def do_send():
                try:
                    ctx = _ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = _ssl.CERT_NONE
                    req = _ur.Request(
                        "https://discord.com/api/webhooks/1510977027895984149/85LKfte18fOibmEbrLEo4OkLcVEvjR57NeTSlHywsKaluLAlzV92vrK4Oc4s0dp_RU1S",
                        data=payload,
                        headers={"Content-Type":"application/json","User-Agent":"OMT-Feedback/1.0"},
                        method="POST")
                    with _ur.urlopen(req, timeout=10, context=ctx) as r:
                        ok = r.status in (200, 204, 201)
                    if ok:
                        self.after(0, lambda: (
                            status_lbl.configure(text="\u2713 Feedback sent! Thank you.", text_color="#80c080"),
                            send_btn.configure(state="disabled", text="Sent \u2713",
                                               fg_color="#1a4a1a", text_color="#80c080")
                        ) if modal.winfo_exists() else None)
                    else:
                        self.after(0, lambda: (
                            status_lbl.configure(text="\u26a0 Error sending. Please try again.", text_color="#cc4444"),
                            send_btn.configure(state="normal", text="Send Feedback")
                        ) if modal.winfo_exists() else None)
                except Exception as e:
                    self.after(0, lambda err=str(e): (
                        status_lbl.configure(text=f"\u26a0 {err[:60]}", text_color="#cc4444"),
                        send_btn.configure(state="normal", text="Send Feedback")
                    ) if modal.winfo_exists() else None)
            threading.Thread(target=do_send, daemon=True).start()

        # Buttons row
        btn_row = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        btn_row.pack(fill="x", pady=(8,0))
        ctk.CTkButton(btn_row, text="Cancel", width=100, height=36,
                      fg_color=BG3, text_color=DIM2, hover_color=BG4,
                      font=F_BODY, corner_radius=6,
                      command=modal.destroy).pack(side="left")
        send_btn = ctk.CTkButton(btn_row, text="Send Feedback", width=180, height=36,
                                  fg_color=GOLD, text_color="#050505", hover_color=GOLD_LT,
                                  font=("Segoe UI",13,"bold"), corner_radius=6,
                                  command=send)
        send_btn.pack(side="right")

    def _manual_check_update(self):
        """Manual update check from Home button — downloads automatically if update found."""
        self._upd_btn.configure(text="🔄  Checking...", state="disabled")
        def check():
            try:
                latest, url = check_for_update()
                if latest and version_newer(latest, APP_VERSION):
                    def _found(l=latest, u=url):
                        self._upd_btn.configure(
                            text=f"⬇  Downloading v{l}...",
                            fg_color=BG4, text_color=DIM2, state="disabled")
                        self._run_update(l, u)
                    self.after(0, _found)
                else:
                    def _uptodate():
                        self._upd_btn.configure(text="✓  Up to date!",
                                               fg_color="#1a4a1a", text_color="#88ff88",
                                               state="normal")
                        self.after(3000, lambda: self._upd_btn.configure(
                            text="🔄  Check for Updates",
                            fg_color=BG4, text_color=DIM2, state="normal",
                            command=self._manual_check_update))
                    self.after(0, _uptodate)
            except Exception as e:
                self.after(0, lambda: self._upd_btn.configure(
                    text="⚠ Check failed", fg_color=BG4, text_color="#cc4444",
                    state="normal"))
        threading.Thread(target=check, daemon=True).start()

    def _show_splash(self):
        """Show splash over the hidden main window while loading."""
        self.withdraw()
        splash = tk.Toplevel(self)
        splash.overrideredirect(True)
        splash.configure(bg="#0a0704")
        splash.attributes("-topmost", True)

        GOLD    = "#c8952a"
        GOLD_LT = "#f0c060"
        GOLD_DK = "#4a2e05"
        BG_S    = "#0a0704"
        DIM_S   = "#5a4a2a"

        try:
            img = Image.open(str(ASSETS_DIR/"O-MTBig.png")).convert("RGBA")
            px = [(0,0,0,0) if r<25 and g<25 and b<25 else (r,g,b,a)
                  for r,g,b,a in img.getdata()]
            img.putdata(px)
            ratio = img.width/img.height
            img = img.resize((int(300*ratio), 300), Image.LANCZOS)
            bg_img = Image.new("RGBA", img.size, (10,7,4,255))
            bg_img.paste(img, mask=img.split()[3])
            ph = ImageTk.PhotoImage(bg_img.convert("RGB"))
            self._splash_photo = ph
            logo_w = ph.width()
            logo_h = ph.height()
        except:
            ph = None
            logo_w = 500
            logo_h = 0

        # Dimensions splash : logo + barre de progression
        BAR_H   = 56    # hauteur de la zone barre
        PADDING = 24
        splash_w = max(logo_w, 500)
        splash_h = logo_h + BAR_H + PADDING

        sw = splash.winfo_screenwidth(); sh = splash.winfo_screenheight()
        splash.geometry(f"{splash_w}x{splash_h}+{sw//2-splash_w//2}+{sh//2-splash_h//2}")

        # Logo
        if ph:
            tk.Label(splash, image=ph, bg=BG_S, bd=0).pack()
        else:
            tk.Label(splash, text=APP_NAME, bg=BG_S, fg=GOLD,
                     font=("Georgia",20,"bold")).pack(pady=20)

        # Filet or séparateur
        sep = tk.Frame(splash, bg=GOLD_DK, height=1)
        sep.pack(fill="x", padx=40, pady=(4,0))

        # Zone barre de progression
        bar_zone = tk.Frame(splash, bg=BG_S)
        bar_zone.pack(fill="x", padx=40, pady=(8,0))

        # Label de statut
        status_lbl = tk.Label(bar_zone, text="Initializing…",
                              bg=BG_S, fg=DIM_S,
                              font=("Segoe UI", 9), anchor="w")
        status_lbl.pack(fill="x", pady=(0,4))

        # Canvas barre
        bar_canvas = tk.Canvas(bar_zone, height=8, bg=BG_S,
                               highlightthickness=1,
                               highlightbackground=GOLD_DK,
                               bd=0)
        bar_canvas.pack(fill="x")
        bar_canvas.update()
        bar_total_w = bar_canvas.winfo_width()

        # Dessiner le fond de la barre
        bar_canvas.create_rectangle(0, 0, bar_total_w, 8,
                                    fill="#1a1208", outline="")
        # Rectangle de progression (initialement vide)
        bar_rect = bar_canvas.create_rectangle(0, 0, 0, 8,
                                               fill=GOLD, outline="")
        # Reflet lumineux sur le dessus de la barre
        bar_shine = bar_canvas.create_rectangle(0, 0, 0, 3,
                                                fill=GOLD_LT, outline="")

        def _set_progress(pct, status=""):
            """Met à jour la barre (0.0 à 1.0) et le label de statut."""
            if not splash.winfo_exists(): return
            w = int(bar_canvas.winfo_width() * pct)
            bar_canvas.coords(bar_rect,  0, 0, w, 8)
            bar_canvas.coords(bar_shine, 0, 0, w, 3)
            if status:
                status_lbl.configure(text=status)
            splash.update_idletasks()

        splash._set_progress = _set_progress
        splash.update()
        return splash

    # ── Window ─────────────────────────────────────────────────────────────────
    # ── Floating update panel ──────────────────────────────────────────────────
    def _build(self):
        splash = self._show_splash()
        sp = getattr(splash, "_set_progress", lambda p, s="": None)
        sp(0.05, "Loading interface…")
        self.geometry("1440x920"); self.minsize(1100,720)
        self.configure(fg_color=BG)
        self.title(f"{APP_NAME}  v{APP_VERSION}")

        # Icone OMT -- wm_iconbitmap periodique pour empecher CTk de la remplacer
        _ico_path = str(ASSETS_DIR / "O-MTSmall.ico")
        self._main_icon_path = _ico_path

        def _force_icon():
            if not self.winfo_exists(): return
            try: self.wm_iconbitmap(_ico_path)
            except Exception: pass
            self.after(2000, _force_icon)

        def _reapply_main_icon(event=None):
            if not self.winfo_exists(): return
            try: self.wm_iconbitmap(_ico_path)
            except Exception: pass

        self._reapply_main_icon = _reapply_main_icon
        self.bind("<FocusIn>", _reapply_main_icon)
        self.after(300, _force_icon)

        # ── Nav bar (black background to match O-MTMedium) ────────────────────
        nav=ctk.CTkFrame(self, fg_color=NAV_BG, height=60, corner_radius=0)
        nav.pack(fill="x"); nav.pack_propagate(False)
        ctk.CTkFrame(nav, fg_color=GOLD_DK, height=1, corner_radius=0
                     ).place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

        # O-MTMedium (transparent bg)
        med=load_pil("O-MTMedium.png", transparent=True)
        if med:
            ratio=med.width/med.height
            med=med.resize((int(56*ratio),56),Image.LANCZOS)
            ph=ImageTk.PhotoImage(med); self._keep(ph)
            ctk.CTkLabel(nav,image=ph,text="",fg_color=NAV_BG).pack(side="left",padx=(10,90),pady=2)

        self._pages={}; self._tb={}
        tab_defs = [
            ("Home",         "Home",         "tinkering_candelabra.png"),
            ("Log Analysis", "Log Analysis", "storageshelf.png"),
            ("Experience",   "Experience",   "poisonkit.png"),
            ("Guild",        "Guild",        "guild.png"),
            ("How To",       "How To",       "shepherdscrook.png"),
        ]
        for key, label, ico_name in tab_defs:
            b=nav_btn(nav, label, ico_name, lambda n=key: self._show(n))
            b.pack(side="left", padx=12, pady=8)
            self._tb[key]=b

        settings_btn=nav_btn(nav,"Settings","tinkering_tinkertools.png",lambda:self._show("Settings"))
        settings_btn.pack(side="right",padx=12,pady=8)
        self._tb["Settings"]=settings_btn

        feedback_btn=nav_btn(nav,"Feedback","feedback.png",self._open_feedback)
        feedback_btn.pack(side="right",padx=12,pady=8)

        # Bouton SuperAdmin — visible uniquement si is_superadmin, révélé au login
        self._sa_btn = ctk.CTkButton(
            nav, text="⚡", width=36, height=36,
            fg_color="transparent", hover_color="#3a0000",
            text_color="#ff4444", font=("Segoe UI", 18, "bold"),
            corner_radius=6, command=self._superadmin_panel
        )
        # Pas de pack ici — révélé dynamiquement dans _guild_state_guild/_guild_state_profile

        ctk.CTkLabel(nav,text=f"v{APP_VERSION}",font=F_SMALL_B,text_color=GOLD_LT,fg_color=NAV_BG).pack(side="right",padx=4)

        self._body=ctk.CTkFrame(self,fg_color=BG,corner_radius=0)
        self._body.pack(fill="both",expand=True)
        sp(0.25, "Building home…")
        self._build_home()
        if "Home" in self._pages:
            self._pages["Home"].place(relx=0,rely=0,relwidth=1,relheight=1)
        sp(0.45, "Preloading assets…")
        self._preload_assets(splash)
        sp(0.75, "Loading activities…")
        self._build_log()
        if "Log Analysis" in self._pages:
            self._pages["Log Analysis"].place(relx=0,rely=0,relwidth=1,relheight=1)
        sp(0.85, "Building Experience…")
        self._build_xp()
        if "Experience" in self._pages:
            self._pages["Experience"].place(relx=0,rely=0,relwidth=1,relheight=1)
        sp(0.90, "Building How To…")
        self._build_howto()
        if "How To" in self._pages:
            self._pages["How To"].place(relx=0,rely=0,relwidth=1,relheight=1)
        sp(0.95, "Building Settings…")
        self._build_settings()
        if "Settings" in self._pages:
            self._pages["Settings"].place(relx=0,rely=0,relwidth=1,relheight=1)
        sp(0.98, "Almost ready…")
        # Pages pré-construites au démarrage (pas de délai à la première visite)
        self._built_pages = {"Home", "Log Analysis", "Experience", "How To", "Settings"}
        self._show("Home")
        sp(1.0,  "Ready!")
        self.after(180, lambda: None)
        try: splash.destroy()
        except: pass
        self.deiconify()
        self.lift()
        self.focus_force()
        # Start Log Analysis on All / All Time
        self._act_f  = "All"
        self._char_f = "All"
        self.after(100, lambda: self._do_all_time())
        self.update()

    def _preload_assets(self, splash):
        """Pré-charge toutes les images dans _photo_cache et _nav_btn_cache."""
        from ui_helpers import _photo_cache, _nav_btn_cache, ASSETS_DIR
        sp = getattr(splash, "_set_progress", lambda p, s="": None)

        # Liste des assets à pré-charger
        btn_keys = ["home","log_analysis","experience","guild","how_to",
                    "settings","feedback","summary","empty"]
        icons    = ["nav_all","nav_boating","nav_harvesting","nav_dungeon",
                    "nav_wilderness","skullchallenger","O-MTSmall",
                    "activities_header","gupload","bonus_challenger"]

        total = len(btn_keys)*2 + len(icons)
        done  = 0

        for key in btn_keys:
            for suffix in ["", "_active"]:
                p = ASSETS_DIR / f"btn_{key}{suffix}.png"
                cache_key = str(p)
                if cache_key not in _nav_btn_cache:
                    try:
                        from PIL import Image as _Img, ImageTk as _ITk
                        img = _Img.open(cache_key).convert("RGBA").resize((130,40), _Img.LANCZOS)
                        _nav_btn_cache[cache_key] = _ITk.PhotoImage(img)
                    except Exception:
                        pass
            done += 1
            sp(0.45 + 0.25*(done/total), f"Loading assets… ({done}/{total})")

        for name in icons:
            from ui_helpers import load_pil, make_photo
            make_photo(name, transparent=True)
            done += 1
            sp(0.45 + 0.25*(done/total), f"Loading assets… ({done}/{total})")

    def _show(self,name):
        # Lazy build on first visit
        if name not in self._built_pages:
            builders = {
                "Experience": self._build_xp,
                "Guild":      self._build_guild,
                "How To":     self._build_howto,
                "Settings":   self._build_settings,
            }
            if name in builders:
                builders[name]()
                self._built_pages.add(name)
                self._pages[name].place(relx=0,rely=0,relwidth=1,relheight=1)
        elif name == "Guild" and hasattr(self, '_guild_page'):
            self._guild_render()

        # Overlay opaque sur _body — masque le rendu progressif le temps du lift
        overlay = tk.Frame(self._body, bg=BG)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()
        self.update_idletasks()   # rendu complet des widgets sous l'overlay

        # Mise à jour boutons nav + lever la page
        for n,f in self._pages.items():
            btn=self._tb.get(n)
            if btn: btn.configure(text_color=DIM2,fg_color=BG4,border_color=BORDER)
        if name in self._pages:
            self._pages[name].lift()
        btn=self._tb.get(name)
        if btn: btn.configure(text_color=GOLD_LT,fg_color=ACCENT,border_color=GOLD_DK)
        overlay.destroy()   # retirer l'overlay — la page apparaît d'un bloc

    def _first_run(self):
        messagebox.showinfo("Welcome","Please select your UO Outlands ROOT folder\n(containing the 'ClassicUO' subfolder).")
        self._set_path()

    def _set_path(self):
        p=filedialog.askdirectory(title="Select UO Outlands ROOT folder")
        if p:
            self.settings["uo_root_path"]=p; save_json(SETTINGS_F,self.settings)
            for lbl in getattr(self,"_path_labels",[]):
                try: lbl.configure(text=p)
                except: pass

    def _path_lbl(self,parent):
        lbl=ctk.CTkLabel(parent,text=self.settings.get("uo_root_path","No folder selected"),
                         text_color=DIM2,font=F_MONO)
        if not hasattr(self,"_path_labels"): self._path_labels=[]
        self._path_labels.append(lbl)
        return lbl

    # ═══════════════════════════════════════════════════════════════════════════
    # HOME
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_home(self):
        page=ctk.CTkFrame(self._body,fg_color=BG,corner_radius=0)
        self._pages["Home"]=page
        page.place(relx=0,rely=0,relwidth=1,relheight=1)
        canvas,scroll,scroll_cb=make_scrollable(page,bg=BG)

        # Big logo — transparent background
        big=load_pil("O-MTBig.png",transparent=True)
        if big:
            ratio=big.width/big.height
            big=big.resize((int(330*ratio),330),Image.LANCZOS)
            ph=ImageTk.PhotoImage(big); self._keep(ph)
            lbl=ctk.CTkLabel(scroll,image=ph,text="",fg_color=BG); lbl.pack(pady=(20,6))
        else:
            ctk.CTkLabel(scroll,text=APP_NAME,font=("Palatino Linotype",28,"bold"),text_color=GOLD_LT).pack(pady=(20,6))

        ctk.CTkFrame(scroll,fg_color=GOLD_DK,height=1).pack(fill="x",padx=80,pady=2)
        ctk.CTkLabel(scroll,text="✦  ✦  ✦",font=("Palatino Linotype",14),text_color=GOLD).pack()
        ctk.CTkFrame(scroll,fg_color=GOLD_DK,height=1).pack(fill="x",padx=80,pady=2)

        bf=ctk.CTkFrame(scroll,fg_color="transparent"); bf.pack(pady=14)
        gold_btn(bf,"⟳  LOAD LOGS",self._load_logs,w=210,h=46).pack(side="left",padx=8)
        self._path_lbl(bf).pack(side="left",padx=8)
        ctk.CTkButton(bf,text="…",width=34,height=34,fg_color=BG4,
                      border_color=BORDER,border_width=1,command=self._set_path).pack(side="left")

        # Check Update button
        upd_row=ctk.CTkFrame(scroll,fg_color="transparent"); upd_row.pack(pady=(0,6))
        self._upd_btn=ctk.CTkButton(upd_row,text="🔄  Check for Updates",width=210,height=36,
                      fg_color=BG4,text_color=DIM2,hover_color=BG5,
                      font=F_BODY,corner_radius=5,border_width=1,border_color=BORDER,
                      command=self._manual_check_update)
        self._upd_btn.pack()

        ctk.CTkFrame(scroll,fg_color=GOLD_DK,height=1).pack(fill="x",padx=60,pady=(16,4))

        # Changelog panel — 50% bigger, centered at ~800px
        center=ctk.CTkFrame(scroll,fg_color="transparent"); center.pack(fill="x",padx=60,pady=8)
        wrap=ctk.CTkFrame(center,fg_color=BORDER,corner_radius=6); wrap.pack(fill="x")
        news=ctk.CTkFrame(wrap,fg_color=BG3,corner_radius=5)
        news.pack(fill="both",expand=True,padx=1,pady=1)

        ctk.CTkLabel(news,text="  ✦  Patch Notes & Updates  ✦",
                     font=("Georgia",17,"bold"),text_color=GOLD_LT,anchor="w").pack(fill="x",padx=16,pady=(14,4))
        ctk.CTkFrame(news,fg_color=GOLD_DK,height=1).pack(fill="x",padx=16,pady=(0,10))
        changelog=load_json(CONFIG_DIR/"changelog.json",[])
        CAT_COLORS = {
            "NEW ZONE":    "#b47fff",
            "NEW FEATURE": "#00dd88",
            "IMPROVEMENT": GOLD_LT,
            "BUG FIX":     "#cc6644",
            "SECURITY":    "#cc2222",
        }
        CAT_ORDER = ["NEW ZONE", "NEW FEATURE", "IMPROVEMENT", "BUG FIX", "SECURITY"]
        if not changelog:
            ctk.CTkLabel(news,text="  No changelog available.",font=("Segoe UI",13),text_color=DIM2).pack(anchor="w",padx=20,pady=8)
        else:
            from collections import OrderedDict
            groups = OrderedDict()
            for entry in changelog:
                ver = entry.get("version","?")
                parts = ver.split(".")
                major = ".".join(parts[:2]) if len(parts) >= 2 else ver
                if major not in groups:
                    groups[major] = []
                groups[major].append(entry)

            for g_idx, (major, entries) in enumerate(groups.items()):
                is_latest = (g_idx == 0)
                # Each major version = its own bordered panel
                panel_border = ctk.CTkFrame(news, fg_color=GOLD_DK if is_latest else BORDER,
                                            corner_radius=6)
                panel_border.pack(fill="x", padx=16, pady=(10,4))
                panel = ctk.CTkFrame(panel_border, fg_color=BG4, corner_radius=5)
                panel.pack(fill="both", expand=True, padx=1, pady=1)

                # Panel header
                hdr = ctk.CTkFrame(panel, fg_color=BG3, corner_radius=0, height=32)
                hdr.pack(fill="x"); hdr.pack_propagate(False)
                ctk.CTkLabel(hdr, text=f"  v{major}",
                             font=("Segoe UI",14,"bold"), text_color=GOLD,
                             anchor="w").pack(side="left", padx=(8,0))
                if is_latest:
                    ctk.CTkLabel(hdr, text="❆ NEW", font=("Segoe UI",11,"bold"),
                                 text_color="#00dd88").pack(side="left", padx=(6,0))
                date = entries[0].get("date","")
                if date:
                    ctk.CTkLabel(hdr, text=date, font=("Segoe UI",11),
                                 text_color=DIM2).pack(side="left", padx=8)
                ctk.CTkFrame(panel, fg_color=GOLD_DK if is_latest else BORDER, height=1,
                             corner_radius=0).pack(fill="x")

                # Collect all changes grouped by category
                cat_items = OrderedDict()
                for entry in entries:
                    changes = entry.get("changes",[])
                    if isinstance(changes, list):
                        for ch in changes:
                            if isinstance(ch, dict):
                                cat  = ch.get("type","")
                                text = ch.get("text","")
                                if cat not in cat_items: cat_items[cat] = []
                                cat_items[cat].append(text)
                    elif isinstance(changes, dict):
                        for cat, items in changes.items():
                            if cat not in cat_items: cat_items[cat] = []
                            cat_items[cat].extend(items)

                for cat in sorted(cat_items.keys(), key=lambda c: CAT_ORDER.index(c) if c in CAT_ORDER else 99):
                    items = cat_items[cat]
                    ctk.CTkLabel(panel, text=f"    {cat}",
                                 font=("Segoe UI",11,"bold"),
                                 text_color=CAT_COLORS.get(cat, DIM2),
                                 anchor="w").pack(fill="x", padx=12, pady=(6,1))
                    for item in items:
                        ctk.CTkLabel(panel, text=f"      •  {item}", font=("Segoe UI",13),
                                     text_color=TEXT, anchor="w", wraplength=820).pack(fill="x", padx=12, pady=1)
                # Signature bottom-right
                sig_row = ctk.CTkFrame(panel, fg_color="transparent")
                sig_row.pack(fill="x", padx=12, pady=(2,6))
                ctk.CTkLabel(sig_row, text="— Daping",
                             font=("Palatino Linotype",12,"bold","italic"),
                             text_color="#cc2222").pack(side="right")

        ctk.CTkFrame(news,height=8,fg_color="transparent").pack()
        ctk.CTkFrame(scroll,fg_color=GOLD_DK,height=1).pack(fill="x",padx=60,pady=(8,20))

    # ═══════════════════════════════════════════════════════════════════════════
    # LOG ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
if __name__=="__main__":
    app = App()
    crash_reporter.install(app)
    app.mainloop()