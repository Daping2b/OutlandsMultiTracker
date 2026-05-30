"""
Outlands Multi Tracker v0.3
By Daping — Windows
"""
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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

VER_DATA    = load_json(CONFIG_DIR/"version.json", {"version":"0.43","app_name":"Outlands Multi Tracker"})
APP_VERSION = VER_DATA.get("version","0.3")
APP_NAME    = VER_DATA.get("app_name","Outlands Multi Tracker")
SETTINGS_F  = CONFIG_DIR / "settings.json"
SESSIONS_F  = DATA_DIR   / "sessions.json"
XP_F        = DATA_DIR   / "xp_data.json"

# ── Palette ────────────────────────────────────────────────────────────────────
BG       = "#080808"
BG2      = "#0f0f0f"   # nav bar bg — must match O-MTMedium background (black)
BG3      = "#181818"
BG4      = "#222222"
BG5      = "#2c2c2c"
GOLD     = "#c8952a"
GOLD_LT  = "#f0c060"
GOLD_DK  = "#4a2e05"
TEXT     = "#e8dcc8"
DIM      = "#504030"
DIM2     = "#907860"
RED      = "#cc3333"
ACCENT   = "#1a2840"
ACCENT2  = "#243655"
BORDER   = "#3a2e18"
ROW_A    = "#141410"
ROW_B    = "#0e0e0c"
DETAIL_BG   = BG3
DETAIL_CARD = BG4
DETAIL_CH   = "#2a2010"
DETAIL_TEXT = TEXT
DETAIL_GOLD = GOLD_LT
DETAIL_DIM  = DIM2

# Nav bar background must match O-MTMedium image background (pure black)
NAV_BG   = "#000000"

ASPECT_COLORS = {
    "Air":       "#a1afbe",   # light blue-grey
    "Arcane":    "#8b67be",   # purple
    "Artisan":   "#beb09d",   # warm beige
    "Blood":     "#c85040",   # deep red
    "Command":   "#6aaa66",   # green
    "Death":     "#aaaaaa",   # grey
    "Discipline":"#be976f",   # tan/orange
    "Earth":     "#a07840",   # brown
    "Eldritch":  "#be6080",   # rose/pink
    "Fire":      "#dd7722",   # orange-red
    "Fortune":   "#ddcc44",   # gold-yellow
    "Frost":     "#88ccee",   # light blue
    "Gadget":    "#c8b890",   # pale gold
    "Harvest":   "#88bb44",   # yellow-green
    "Holy":      "#eedd88",   # pale gold/white
    "Lightning": "#ffee44",   # bright yellow
    "Lyric":     "#cc99aa",   # pink-purple
    "Madness":   "#cc3355",   # crimson-pink
    "Poison":    "#99bb44",   # yellow-green
    "Shadow":    "#887799",   # grey-purple
    "Void":      "#8877bb",   # blue-purple
    "War":       "#cc6633",   # orange-brown
    "Water":     "#5588cc",   # blue
}
CAT_ICONS = {
    "Gold & Currency":"💰","Unidentified Items":"📜","Maps":"🗺",
    "Logs":"🪵","Ores":"⛏","Ingots":"🔩","Boards":"🪚","Leather":"🐾",
    "Aspects & Phylacteries":"✨","Skill Mastery":"⭐","Runes":"🔮","Seeds":"🌱",
    "Collectable Cards":"🃏","Mastery Chain Links":"⛓","Gems":"💎",
    "Crafting Materials":"⚗","Dyes & Rare Cloth":"🎨","Paragon":"👑",
    "Miscellaneous":"📦","__xp__":"🌟",
}

F_TITLE  = ("Palatino Linotype", 14, "bold")
F_BODY   = ("Segoe UI", 14)
F_BODY_B = ("Segoe UI", 14, "bold")
F_SMALL  = ("Segoe UI", 12)
F_SMALL_B= ("Segoe UI", 12, "bold")
F_MONO   = ("Consolas", 11)
F_HEAD   = ("Georgia", 18, "bold")
F_BIG    = ("Georgia", 23, "bold")
F_NAV    = ("Segoe UI", 13, "bold")

# Icon sizes
SZ_NAV   = (22, 22)   # nav button icons
SZ_COL   = (18, 18)   # column header icons

# ── Image loading ──────────────────────────────────────────────────────────────
_img_cache = {}

def _hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def make_transparent(img, threshold=30):
    """Make near-black pixels transparent (removes black backgrounds from UO icons)."""
    img = img.convert("RGBA")
    data = img.getdata()
    new = []
    for r,g,b,a in data:
        if r < threshold and g < threshold and b < threshold:
            new.append((0,0,0,0))
        else:
            new.append((r,g,b,a))
    img.putdata(new)
    return img

def load_pil(name, size=None, transparent=False):
    key = (name, size, transparent)
    if key in _img_cache: return _img_cache[key]
    p = Path(_ap(name))
    if not p.exists():
        return None
    try:
        img = Image.open(str(p)).convert("RGBA")
        if transparent:
            img = make_transparent(img)
        if size: img = img.resize(size, Image.LANCZOS)
        _img_cache[key] = img
        return img
    except Exception as e:
        return None

def make_photo(name, size=None, transparent=False):
    pil = load_pil(name, size, transparent)
    return ImageTk.PhotoImage(pil) if pil else None

# ── Icon loading helper ────────────────────────────────────────────────────────
_icon_photos = []   # keep alive

def icon(name, size=SZ_NAV):
    ph = make_photo(name, size, transparent=True)
    if ph: _icon_photos.append(ph)
    return ph

# ── Categorisation ─────────────────────────────────────────────────────────────
def categorise_item(desc):
    d = desc.lower().strip()
    if "paragon"         in d: return "Paragon"
    if "unidentified"    in d: return "Unidentified Items"
    if any(x in d for x in ["treasure map","fishing map","skinning map","ore map","lumber map"]): return "Maps"
    if re.search(r'\b(log|logs)\b', d): return "Logs"
    if re.search(r'\bore\b', d):        return "Ores"
    if "ingot"           in d: return "Ingots"
    if any(w in d for w in ["board","dullwood","goldenwood","shadowwood","rosewood","verewood","valewood","bronzewood","copperwood","avarwood"]): return "Boards"
    if any(w in d for w in ["dullhide","shadowhide","copperhide","bronzehide","goldenhide","rosehide","verehide","valehide","avarhide"]): return "Leather"
    if any(x in d for x in ["aspect core","aspect distillation","phylactery","chromatic core","chromatic distillation"]): return "Aspects & Phylacteries"
    if "skill mastery"   in d: return "Skill Mastery"
    if "rune ("          in d: return "Runes"
    if "seed"            in d: return "Seeds"
    if "collectable card" in d: return "Collectable Cards"
    if "mastery chain"   in d: return "Mastery Chain Links"
    if d in {"amber","amethyst","citrine","diamond","emerald","ruby","sapphire","star sapphire","tourmaline"} or "gem" in d: return "Gems"
    if any(x in d for x in ["arcane essence","research material","plant chemical","blank scroll","arcane scroll","mastercrafting"]): return "Crafting Materials"
    if any(x in d for x in ["dye","rare cloth","carpet dye","headwear dye","mount gear dye"]): return "Dyes & Rare Cloth"
    if "gold coin"  in d: return "Gold & Currency"
    if "doubloon"   in d: return "Gold & Currency"
    return "Miscellaneous"

RARE_CATS    = {"Aspects & Phylacteries","Skill Mastery","Collectable Cards","Mastery Chain Links","Dyes & Rare Cloth","Maps","Miscellaneous","Crafting Materials","Paragon"}
HARVEST_CATS = {"Logs","Ores"}
JUNK_CATS    = {"Unidentified Items"}

# ── Polygon ────────────────────────────────────────────────────────────────────
def point_in_polygon(x, y, polygon):
    n=len(polygon); inside=False; px,py=polygon[0]
    for i in range(1,n+1):
        nx_,ny_=polygon[i%n]
        if ((py>y)!=(ny_>y)) and (x<(nx_-px)*(y-py)/(ny_-py+1e-12)+px): inside=not inside
        px,py=nx_,ny_
    return inside

def detect_zone(x, y, dung, wild):
    for d in dung.get("dungeons",[]):
        p=d.get("polygon",[])
        if len(p)>=3 and point_in_polygon(x,y,p): return d["name"]
    for w in wild.get("wilderness",[]):
        p=w.get("polygon",[])
        if len(p)>=3 and point_in_polygon(x,y,p): return w["name"]
    return None

# ── Log parser ─────────────────────────────────────────────────────────────────
LOG_RE = re.compile(r'^\[(\d{2}/\d{2}/\d{4} \d{2}:\d{2})\]\s+([^:]+):\s*(.*)$')
TS_FMT = "%m/%d/%Y %H:%M"

def parse_logs(log_files, dung, wild, known_ids, progress_cb=None):
    sessions=[]; xp_events=[]; total=len(log_files); done=0
    for fpath in sorted(log_files):
        done+=1
        if progress_cb: progress_cb(done, total, fpath.name)
        fid=str(fpath)
        if fid in known_ids: continue
        known_ids.add(fid)
        try: lines=Path(fpath).read_text(encoding="utf-8",errors="replace").splitlines()
        except: continue
        ptl=[]
        for line in lines:
            m=LOG_RE.match(line)
            if not m: continue
            try: ts=datetime.strptime(m.group(1).strip(),TS_FMT)
            except: continue
            if m.group(2).strip()=="System":
                msg=m.group(3).strip()
                if msg.startswith("Welcome ") and msg.endswith("!"): ptl.append((ts,msg[8:-1]))
        def get_player(ts):
            name=""
            for pt,pn in ptl:
                if pt<=ts: name=pn
                else: break
            return name
        cur=None; asp_first={}
        for line in lines:
            m=LOG_RE.match(line)
            if not m: continue
            try: ts=datetime.strptime(m.group(1).strip(),TS_FMT)
            except: continue
            author=m.group(2).strip(); msg=m.group(3).strip()
            is_razor=(author in ("[Razor]","Razor"))
            if is_razor and "═ RECORDING" in msg and "▶" in msg:
                cur={"player":get_player(ts),"type":"Unknown","start":ts,"end":None,"location":None,"loots":{},"aspects":{}}
                asp_first={}; continue
            if cur is None: continue
            if is_razor and "◆" in msg:
                stype=msg.replace("◆","").strip()
                if any(k in stype for k in ["Farming","Boating","Harvest","Session"]):
                    cur["type"]=stype
                    p=get_player(ts)
                    if p: cur["player"]=p
            loc_m=re.search(r'Current location is \((\d+),\s*(\d+),',msg)
            if loc_m and author=="System":
                lx,ly=int(loc_m.group(1)),int(loc_m.group(2))
                zone=detect_zone(lx,ly,dung,wild)
                if zone: cur["location"]=zone
            if is_razor and "●" in msg:
                lm=re.search(r'● \d+ (.+?)(?:\s*:\s*(\d+))?$',msg)
                if lm:
                    iname=lm.group(1).strip(); qty=int(lm.group(2)) if lm.group(2) else 1
                    cat=categorise_item(iname)
                    cur["loots"].setdefault(cat,{})
                    cur["loots"][cat][iname]=cur["loots"][cat].get(iname,0)+qty
            xp_m=re.search(r'\((\w+) Aspect ([\d,\.]+)/([\d,]+) xp\)',msg)
            if xp_m:
                asp=xp_m.group(1); xp_cur=float(xp_m.group(2).replace(",","")); xp_max=float(xp_m.group(3).replace(",",""))
                player=cur.get("player","")
                xp_events.append({"ts":ts,"player":player,"aspect":asp,"xp_cur":xp_cur,"xp_max":xp_max})
                asp_first.setdefault(asp,(xp_cur,xp_max))
                cur["aspects"][asp]=(xp_cur,xp_max,asp_first[asp])
            if is_razor and ("SESSION END" in msg or "SESSION : ENDING" in msg):
                cur["end"]=ts
                p=get_player(ts)
                if p: cur["player"]=p
                gained={}
                for asp,(cv,mx,(fv,fmx)) in cur["aspects"].items():
                    gained[asp]=(cv-fv) if cv>=fv else (fmx-fv)+cv
                cur["aspects_gained"]=gained; sessions.append(cur); cur=None; asp_first={}
    return sessions, xp_events

# ── Metrics ────────────────────────────────────────────────────────────────────
def dur_min(s):
    if s.get("end") and s.get("start"): return max(1,(s["end"]-s["start"]).total_seconds()/60)
    return 1
def s_gold(s):    return sum(q for c,it in s.get("loots",{}).items() if c=="Gold & Currency" for n,q in it.items() if "gold"     in n.lower())
def s_doub(s):    return sum(q for c,it in s.get("loots",{}).items() if c=="Gold & Currency" for n,q in it.items() if "doubloon" in n.lower())
def s_rare(s):    return sum(q for c,it in s.get("loots",{}).items() if c in RARE_CATS    for q in it.values())
def s_junk(s):    return sum(q for c,it in s.get("loots",{}).items() if c in JUNK_CATS    for q in it.values())
def s_harvest(s): return sum(q for c,it in s.get("loots",{}).items() if c in HARVEST_CATS for q in it.values())
def s_exp(s):     return sum(s.get("aspects_gained",{}).values())
def rate(total,mins):
    r=total/max(1,mins); return f"{r/1000:.1f}k/min" if r>=1000 else f"{r:.1f}/min"
def fmt_dur(mins):
    m=int(mins); h,mm=divmod(m,60); return f"{h}h{mm:02d}m" if h else f"{mm}m"
def type_display(s):
    t=s.get("type","Unknown")
    if "Creature Farming" in t:
        loc=s.get("location"); return loc if loc else "Dungeon"
    return t
def session_date(s):
    if s.get("start"): return s["start"].strftime("%Y-%m-%d\n%H:%M")
    return "—"

def discord_text(sessions):
    lines=["```","═══ OUTLANDS MULTI TRACKER ═══"]
    for s in sessions:
        mins=dur_min(s)
        lines+=[f"[{s.get('player','')}] {type_display(s)} | {fmt_dur(mins)}",
                f"  Gold: {s_gold(s):,} ({rate(s_gold(s),mins)})  Doubloons: {s_doub(s):,} ({rate(s_doub(s),mins)})",
                f"  Rare: {s_rare(s)} ({rate(s_rare(s),mins)})  Junk: {s_junk(s)}  Harvest: {s_harvest(s):,} ({rate(s_harvest(s),mins)})",
                f"  Exp: {s_exp(s):,.0f} ({rate(s_exp(s),mins)})"]
    if len(sessions)>1:
        tm=sum(dur_min(s) for s in sessions)
        tg,td,tr,tj,th,te=(sum(f(s) for s in sessions) for f in [s_gold,s_doub,s_rare,s_junk,s_harvest,s_exp])
        lines+=["─── CUMUL ───",f"Gold: {tg:,} ({rate(tg,tm)})  Doubloons: {td:,} ({rate(td,tm)})",
                f"Rare: {tr} ({rate(tr,tm)})  Junk: {tj}  Harvest: {th:,} ({rate(th,tm)})",
                f"Exp: {te:,.0f} ({rate(te,tm)})",""]
        merged={}
        for s in sessions:
            for cat,items in s.get("loots",{}).items():
                for n,q in items.items(): merged.setdefault(cat,{}).setdefault(n,0); merged[cat][n]+=q
        for cat in sorted(merged):
            lines.append(f"  [{cat}]")
            for n,q in sorted(merged[cat].items()): lines.append(f"    {n}: {q:,}")
    else:
        lines.append("")
        for cat in sorted(sessions[0].get("loots",{})):
            lines.append(f"  [{cat}]")
            for n,q in sorted(sessions[0]["loots"][cat].items()): lines.append(f"    {n}: {q:,}")
    lines.append("```"); return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

def gold_btn(parent, text, cmd, w=140, h=38):
    return ctk.CTkButton(parent,text=text,width=w,height=h,
                         fg_color=GOLD,text_color="#050505",hover_color=GOLD_LT,
                         font=F_BODY_B,corner_radius=5,border_width=1,
                         border_color=GOLD_LT,command=cmd)

def dim_btn(parent, text, cmd, w=110, h=32):
    return ctk.CTkButton(parent,text=text,width=w,height=h,
                         fg_color=BG4,text_color=TEXT,hover_color=ACCENT2,
                         font=F_SMALL,corner_radius=4,border_width=1,
                         border_color=BORDER,command=cmd)

def nav_btn(parent, text, icon_name, cmd):
    ico = icon(icon_name, SZ_NAV)
    if ico:
        return ctk.CTkButton(parent, text=f"  {text}", image=ico, compound="left",
                             width=165, height=46,
                             fg_color=BG4, text_color=DIM2, hover_color=BG5,
                             font=F_NAV, corner_radius=6,
                             border_width=2, border_color=BORDER, command=cmd)
    else:
        return ctk.CTkButton(parent, text=text, width=165, height=46,
                             fg_color=BG4, text_color=DIM2, hover_color=BG5,
                             font=F_NAV, corner_radius=6,
                             border_width=2, border_color=BORDER, command=cmd)

def _bind_scroll(widget, cb):
    """Recursively bind mousewheel to widget and all children."""
    widget.bind("<MouseWheel>", cb)
    for child in widget.winfo_children():
        _bind_scroll(child, cb)

def make_scrollable(parent, bg=None):
    c = bg or BG
    sf=ctk.CTkFrame(parent,fg_color=c,corner_radius=0); sf.pack(fill="both",expand=True)
    canvas=tk.Canvas(sf,bg=c,highlightthickness=0)
    vsb=ctk.CTkScrollbar(sf,command=canvas.yview); vsb.pack(side="right",fill="y")
    canvas.pack(fill="both",expand=True); canvas.configure(yscrollcommand=vsb.set)
    inner=ctk.CTkFrame(canvas,fg_color=c,corner_radius=0)
    wid=canvas.create_window((0,0),window=inner,anchor="nw")
    inner.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>",lambda e:canvas.itemconfig(wid,width=e.width))

    def _scroll(e):
        # Only scroll if mouse is over this canvas
        wx = canvas.winfo_rootx(); wy = canvas.winfo_rooty()
        ww = canvas.winfo_width(); wh = canvas.winfo_height()
        mx = e.x_root; my = e.y_root
        if wx <= mx <= wx+ww and wy <= my <= wy+wh:
            if canvas.yview()[0] <= 0 and e.delta > 0: return
            canvas.yview_scroll(int(-1*(e.delta/120)), "units")

    # Use bind_all on parent so it captures all mousewheel events
    # but filter by position to avoid conflicts between panels
    canvas._scroll_cb = _scroll
    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _scroll))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    return canvas, inner, _scroll

def date_row(parent, cmd_apply, cmd_all):
    row=ctk.CTkFrame(parent,fg_color="transparent"); row.pack(side="left",fill="x")
    ctk.CTkLabel(row,text="From:",text_color=DIM2,font=F_BODY,width=50).pack(side="left",padx=(0,2))
    if HAS_CAL:
        kw=dict(width=12,background=BG4,foreground=TEXT,borderwidth=1,
                date_pattern="yyyy-mm-dd",font=F_SMALL,showweeknumbers=False,
                headersbackground=BG3,headersforeground=GOLD_LT,
                selectbackground=ACCENT2,selectforeground=TEXT,
                normalbackground=BG4,normalforeground=TEXT,
                weekendbackground=BG4,weekendforeground=DIM2,
                othermonthforeground=DIM,othermonthbackground=BG3)
        de_from=DateEntry(row,**kw); de_from.pack(side="left",padx=2)
        ctk.CTkLabel(row,text="To:",text_color=DIM2,font=F_BODY,width=30).pack(side="left",padx=(8,2))
        de_to=DateEntry(row,**kw); de_to.pack(side="left",padx=2)
        _all=[False]
        get_from=lambda: "" if _all[0] else de_from.get_date().strftime("%Y-%m-%d")
        get_to  =lambda: "" if _all[0] else de_to.get_date().strftime("%Y-%m-%d")
        def clear(): _all[0]=False; de_from.set_date(date.today()); de_to.set_date(date.today()); cmd_apply()
        def do_all(): _all[0]=True; cmd_all()
    else:
        de_from=ctk.CTkEntry(row,width=115,placeholder_text="YYYY-MM-DD",font=F_SMALL,fg_color=BG4,border_color=BORDER,text_color=TEXT)
        de_from.pack(side="left",padx=2)
        ctk.CTkLabel(row,text="To:",text_color=DIM2,font=F_BODY,width=30).pack(side="left",padx=(8,2))
        de_to=ctk.CTkEntry(row,width=115,placeholder_text="YYYY-MM-DD",font=F_SMALL,fg_color=BG4,border_color=BORDER,text_color=TEXT)
        de_to.pack(side="left",padx=2)
        get_from=lambda: de_from.get().strip()
        get_to  =lambda: de_to.get().strip()
        def clear(): de_from.delete(0,"end"); de_to.delete(0,"end"); cmd_apply()
        def do_all(): de_from.delete(0,"end"); de_to.delete(0,"end"); cmd_all()

    ctk.CTkButton(row,text="Apply",width=72,height=30,fg_color=ACCENT2,
                  border_color=BORDER,border_width=1,font=F_BODY,
                  command=cmd_apply).pack(side="left",padx=6)
    ctk.CTkButton(row,text="Clear",width=62,height=30,fg_color=BG4,
                  border_color=BORDER,border_width=1,font=F_BODY,
                  command=clear).pack(side="left")
    gold_btn(row,"⏳ All Time",do_all,w=105,h=30).pack(side="left",padx=8)
    return get_from, get_to

# ── Auto-updater ───────────────────────────────────────────────────────────────
def check_for_update():
    """Returns (latest_version, download_url) or (None, None)."""
    import ssl
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(GITHUB_API,
              headers={"User-Agent": "Mozilla/5.0 OutlandsMultiTracker"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            data = json.loads(r.read().decode())
        tag    = data.get("tag_name", "").lstrip("v")
        assets = data.get("assets", [])
        dl_url = next((a["browser_download_url"] for a in assets
                       if a["name"].endswith(".zip")), None)
        if tag and dl_url:
            return tag, dl_url
        # API responded but no zip asset found
        print(f"[UPDATE] No zip asset found in release {tag}")
    except Exception as e:
        print(f"[UPDATE] check_for_update failed: {e}")
    return None, None

def version_newer(remote, local):
    """True if remote > local — supports 0.57, 0.57.1, 0.58 etc."""
    def parts(v):
        try:
            return tuple(int(x) for x in str(v).strip().split("."))
        except:
            return (0,)
    r, l = parts(remote), parts(local)
    # Pad to same length for fair comparison
    maxlen = max(len(r), len(l))
    r = r + (0,) * (maxlen - len(r))
    l = l + (0,) * (maxlen - len(l))
    return r > l

def do_update(download_url, progress_cb=None):
    """Download zip then launch Updater.exe which handles extraction independently."""
    import ssl
    tmp_zip     = BASE_DIR / "_update.zip"
    updater_exe = BASE_DIR / "Updater.exe"
    exe_name    = "OutlandsMultiTracker.exe"  # hardcoded — never rely on sys.executable name

    # Pre-flight checks
    if not download_url:
        raise ValueError("No download URL provided by GitHub API")
    if not updater_exe.exists():
        raise FileNotFoundError(f"Updater.exe not found at {updater_exe}")

    # Clean up any leftover zip
    try:
        if tmp_zip.exists(): tmp_zip.unlink()
    except Exception as e:
        raise RuntimeError(f"Cannot clean up old update file: {e}")

    # ── Download with 2 attempts (different SSL contexts) ─────────────────────
    headers = {"User-Agent": "Mozilla/5.0 OutlandsMultiTracker"}

    def _try_download(url, dest, verify_ssl):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE if not verify_ssl else ssl.CERT_REQUIRED
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
            total = int(r.headers.get("Content-Length", 0))
            done = 0; chunk = 65536; last_cb = 0
            with open(dest, "wb") as f:
                while True:
                    buf = r.read(chunk)
                    if not buf: break
                    f.write(buf); done += len(buf)
                    if progress_cb and total and (done - last_cb) > total * 0.02:
                        progress_cb(done, total, "Downloading...")
                        last_cb = done
            if progress_cb: progress_cb(total or done, total or done, "Downloading...")
        return done

    last_err = None
    for attempt, verify in enumerate([(False), (True)], 1):
        try:
            if progress_cb: progress_cb(0, 1, f"Downloading... (attempt {attempt}/2)")
            size = _try_download(download_url, tmp_zip, verify)
            if size == 0:
                raise RuntimeError("Downloaded file is empty (0 bytes)")
            last_err = None
            print(f"[UPDATE] Download OK — {size/1024:.1f} KB")
            break
        except Exception as e:
            last_err = e
            print(f"[UPDATE] Download attempt {attempt} failed: {e}")
            try: tmp_zip.unlink(missing_ok=True)
            except: pass

    if last_err:
        raise RuntimeError(f"Download failed: {last_err}")

    # Verify zip is valid before launching updater
    import zipfile
    if not zipfile.is_zipfile(str(tmp_zip)):
        try: tmp_zip.unlink(missing_ok=True)
        except: pass
        raise RuntimeError("Downloaded file is not a valid zip archive")

    if progress_cb: progress_cb(0, 1, "Launching installer...")

    # ── Launch Updater.exe ────────────────────────────────────────────────────
    try:
        subprocess.Popen(
            [str(updater_exe), str(tmp_zip), str(BASE_DIR), exe_name],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
            cwd=str(BASE_DIR)
        )
    except Exception as e:
        raise RuntimeError(f"Failed to launch Updater.exe: {e}")

    return True


# ── Update progress modal ─────────────────────────────────────────────────────
class UpdateModal(tk.Toplevel):
    def __init__(self, parent, version):
        super().__init__(parent)
        self.title("Updating...")
        self.configure(bg=BG); self.resizable(False,False)
        self.grab_set(); self.protocol("WM_DELETE_WINDOW", lambda: None)
        w,h=480,180
        px=parent.winfo_x()+parent.winfo_width()//2-w//2
        py=parent.winfo_y()+parent.winfo_height()//2-h//2
        self.geometry(f"{w}x{h}+{px}+{py}")
        border=tk.Frame(self,bg=GOLD,bd=2); border.pack(fill="both",expand=True,padx=2,pady=2)
        inner=tk.Frame(border,bg=BG); inner.pack(fill="both",expand=True)
        tk.Label(inner,text=f"Updating to v{version}",bg=BG,fg=GOLD_LT,
                 font=("Georgia",14,"bold")).pack(pady=(16,4))
        self._lbl=tk.Label(inner,text="Connecting...",bg=BG,fg=DIM2,
                           font=("Segoe UI",11)); self._lbl.pack(pady=2)
        self._pct=tk.Label(inner,text="",bg=BG,fg=TEXT,
                           font=("Segoe UI",11)); self._pct.pack()
        bar_frame=tk.Frame(inner,bg=BG4,height=14,width=420)
        bar_frame.pack(pady=8,padx=20); bar_frame.pack_propagate(False)
        self._fill=tk.Frame(bar_frame,bg=GOLD,height=14)
        self._fill.place(x=0,y=0,relheight=1,width=0); self._bar_w=420

    def update_progress(self,done,total,msg=""):
        pct=done/max(1,total); fw=int(self._bar_w*pct)
        self._fill.place(x=0,y=0,relheight=1,width=fw)
        self._lbl.configure(text=msg[:60])
        if total>1:
            self._pct.configure(text=f"{done/1024/1024:.1f} / {total/1024/1024:.1f} MB  ({int(pct*100)}%)")
        self.update_idletasks()

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
class App(ctk.CTk):
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
        self._sort_col  = None
        self._sort_rev  = False
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        if not self.settings.get("uo_root_path"):
            self.after(800, self._first_run)
        # Check for updates — skip if just updated (flag file present)
        _flag = BASE_DIR / "_just_updated"
        if _flag.exists():
            try: _flag.unlink()
            except: pass
        else:
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
        latest, url = check_for_update()
        if latest and version_newer(latest, APP_VERSION):
            self.after(0, lambda: self._prompt_update(latest, url))

    def _prompt_update(self, version, url):
        # Show update modal and run update automatically
        modal = UpdateModal(self, version)
        self.update_idletasks()
        def progress_cb(done, total, msg):
            self.after(0, lambda: modal.update_progress(done, total, msg))
        _update_err = [None]
        def run():
            ok = False
            try:
                ok = do_update(url, progress_cb)
            except Exception as e:
                ok = False
                _update_err[0] = e
                print(f"[UPDATE] Fatal error: {e}")
            if ok:
                self.after(0, self.destroy)
            else:
                err_msg = str(_update_err[0]) if _update_err[0] else "Unknown error — check internet connection or try downloading manually."
                self.after(0, lambda: modal.destroy())
                self.after(100, lambda m=err_msg: messagebox.showerror("Update failed", f"Error:\n{m}"))
        threading.Thread(target=run, daemon=True).start()

    # ── Bonus helpers ──────────────────────────────────────────────────────────
    BONUS_ICONS = {
        "sanctuary": "bonus_sanctuary.png",
        "challenger": "bonus_challenger.png",
        "respawn":    "bonus_respawn.png",
        "gold_loot":  "bonus_gold_loot.png",
        "experience": "bonus_experience.png",
    }
    BONUS_LABELS = {
        "sanctuary":  "Sanctuary Dungeon",
        "challenger": "Challenger Dungeon",
        "respawn":    "Faster Respawn",
        "gold_loot":  "Gold Loot Bonus",
        "experience": "Experience Bonus",
        "vendor":     "Vendor Rebate",
        "crafting":   "Exceptional Crafting",
    }

    def _fetch_bonuses(self):
        """Download latest bonuses.json from GitHub."""
        try:
            import urllib.request as _ur, ssl
            url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/config/bonuses.json"
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = _ur.Request(url, headers={"User-Agent":"Mozilla/5.0 OutlandsMultiTracker"})
            with _ur.urlopen(req, timeout=10, context=ctx) as r:
                data = json.loads(r.read().decode())
            if data:
                self.bonuses_db = data
                # Force reload of bonus icons on next tree refresh
                self._tree_bonus_photos = {}
                save_json(CONFIG_DIR/"bonuses.json", data)
                self.after(0, self._refresh_bonus_tree)
        except Exception as e:
            print(f"[BONUSES] Fetch failed: {e}")

    def _get_week_key(self, dt=None):
        if dt is None: dt = datetime.now()
        days_since_sat = (dt.weekday() + 2) % 7
        return (dt - timedelta(days=days_since_sat)).strftime("%Y-%m-%d")

    def _get_bonus_for_session(self, s):
        loc = s.get("location")
        if not loc: return None
        start = s.get("start")
        if not start: return None
        week = self.bonuses_db.get(self._get_week_key(start), {})
        if loc in week: return week[loc]
        for k,v in week.items():
            if k.lower() in loc.lower() or loc.lower() in k.lower():
                return v
        return None

    def _get_current_bonuses(self):
        return self.bonuses_db.get(self._get_week_key(), {})

    def _refresh_bonus_tree(self):
        try: self._fill_act_tree()
        except: pass

    def _add_tooltip(self, widget, text):
        tip = [None]
        def enter(e):
            tip[0] = tk.Toplevel(widget)
            tip[0].wm_overrideredirect(True)
            tip[0].wm_geometry(f"+{e.x_root+12}+{e.y_root+6}")
            tk.Label(tip[0], text=text, background="#1a1a1a", foreground=GOLD_LT,
                     font=F_SMALL, relief="solid", borderwidth=1, padx=6, pady=3).pack()
        def leave(e):
            if tip[0]:
                try: tip[0].destroy()
                except: pass
                tip[0] = None
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def _manual_check_update(self):
        """Manual update check triggered from Home page button."""
        self._upd_btn.configure(text="🔄  Checking...", state="disabled")
        def check():
            latest, url = check_for_update()
            if latest and version_newer(latest, APP_VERSION):
                self.after(0, lambda: (
                    self._upd_btn.configure(text=f"⬇  Update to v{latest}!", 
                                           fg_color=GOLD, text_color="#050505",
                                           state="normal",
                                           command=lambda: self._prompt_update(latest, url))
                ))
            else:
                self.after(0, lambda: (
                    self._upd_btn.configure(text="✓  Up to date!", 
                                           fg_color="#1a4a1a", text_color="#88ff88",
                                           state="normal")
                ))
                # Reset button after 3 seconds
                self.after(3000, lambda: self._upd_btn.configure(
                    text="🔄  Check for Updates",
                    fg_color=BG4, text_color=DIM2,
                    command=self._manual_check_update))
        threading.Thread(target=check, daemon=True).start()

    def _show_splash(self):
        """Show splash over the hidden main window while loading."""
        self.withdraw()   # hide main window
        splash = tk.Toplevel(self)
        splash.overrideredirect(True)
        splash.configure(bg="#000000")
        splash.attributes("-topmost", True)
        try:
            img = Image.open(str(ASSETS_DIR/"O-MTBig.png")).convert("RGBA")
            px = [(0,0,0,0) if r<25 and g<25 and b<25 else (r,g,b,a)
                  for r,g,b,a in img.getdata()]
            img.putdata(px)
            ratio = img.width/img.height
            img = img.resize((int(300*ratio),300), Image.LANCZOS)
            bg_img = Image.new("RGBA", img.size, (0,0,0,255))
            bg_img.paste(img, mask=img.split()[3])
            ph = ImageTk.PhotoImage(bg_img.convert("RGB"))
            self._splash_photo = ph   # keep alive on self
            sw = splash.winfo_screenwidth(); sh = splash.winfo_screenheight()
            w,h = ph.width(), ph.height()
            splash.geometry(f"{w}x{h}+{sw//2-w//2}+{sh//2-h//2}")
            tk.Label(splash, image=ph, bg="#000000", bd=0).pack()
        except:
            splash.geometry("500x200")
            tk.Label(splash, text=APP_NAME, bg="#000000", fg="#c8952a",
                     font=("Georgia",20,"bold")).pack(expand=True)
        splash.update()
        return splash

    # ── Window ─────────────────────────────────────────────────────────────────
    def _build(self):
        splash = self._show_splash()
        self.geometry("1440x920"); self.minsize(1100,720)
        self.configure(fg_color=BG)
        self.title(f"{APP_NAME}  v{APP_VERSION}")

        # Window icon — use high quality 128x128 version
        ico_path = str(ASSETS_DIR / "O-MTSmall.ico")
        try:
            self.iconbitmap(ico_path)
        except Exception:
            ico_pil = load_pil("O-MTSmall_128x128.png", (64,64), transparent=True)
            if ico_pil:
                ph=ImageTk.PhotoImage(ico_pil); self._keep(ph)
                self.iconphoto(True, ph)

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
            ctk.CTkLabel(nav,image=ph,text="",fg_color=NAV_BG).pack(side="left",padx=(10,16),pady=2)

        self._pages={}; self._tb={}
        tab_defs = [
            ("Home",         "Home",         "tinkering_candelabra.png"),
            ("Log Analysis", "Log Analysis", "storageshelf.png"),
            ("Experience",   "Experience",   "poisonkit.png"),
            ("How To",       "How To",       "shepherdscrook.png"),
        ]
        for key, label, ico_name in tab_defs:
            b=nav_btn(nav, label, ico_name, lambda n=key: self._show(n))
            b.pack(side="left", padx=4, pady=8)
            self._tb[key]=b

        settings_btn=nav_btn(nav,"Settings","tinkering_tinkertools.png",lambda:self._show("Settings"))
        settings_btn.pack(side="right",padx=8,pady=8)
        self._tb["Settings"]=settings_btn
        ctk.CTkLabel(nav,text=f"v{APP_VERSION}",font=F_SMALL_B,text_color=GOLD_LT,fg_color=NAV_BG).pack(side="right",padx=4)

        self._body=ctk.CTkFrame(self,fg_color=BG,corner_radius=0)
        self._body.pack(fill="both",expand=True)
        self._build_home()
        self._build_log()
        self._build_xp()
        self._build_howto()
        self._build_settings()
        self._show("Home")
        try: splash.destroy()
        except: pass
        self.deiconify()
        self.lift()
        self.focus_force()
        self.update()

    def _show(self,name):
        for n,f in self._pages.items():
            f.pack_forget()
            btn=self._tb.get(n)
            if btn: btn.configure(text_color=DIM2,fg_color=BG4,border_color=BORDER)
        self._pages[name].pack(fill="both",expand=True)
        btn=self._tb.get(name)
        if btn: btn.configure(text_color=GOLD_LT,fg_color=ACCENT,border_color=GOLD_DK)

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
        if not changelog:
            ctk.CTkLabel(news,text="  No changelog available.",font=("Segoe UI",13),text_color=DIM2).pack(anchor="w",padx=20,pady=8)
        else:
            for idx,entry in enumerate(changelog[:8]):
                is_latest = (idx==0)
                vrow=ctk.CTkFrame(news,fg_color="transparent"); vrow.pack(fill="x",padx=20,pady=(10,2))
                # Version badge
                ver_lbl=ctk.CTkLabel(vrow,text=f"v{entry.get('version','?')}",
                             font=("Segoe UI",14,"bold"),text_color=GOLD,width=65,anchor="w")
                ver_lbl.pack(side="left")
                # NEW badge for latest entry
                if is_latest:
                    ctk.CTkLabel(vrow,text=" ✦ NEW",font=("Segoe UI",11,"bold"),
                                 text_color="#00dd88").pack(side="left",padx=(0,8))
                ctk.CTkLabel(vrow,text=entry.get("date",""),font=("Segoe UI",12),text_color=DIM2).pack(side="left",padx=8)
                # Author signature in red
                author=entry.get("author","")
                if author:
                    ctk.CTkLabel(vrow,text=f"— {author}",
                                 font=("Palatino Linotype",12,"bold","italic"),
                                 text_color="#cc2222").pack(side="right",padx=8)
                changes = entry.get("changes", {})
                if isinstance(changes, dict):
                    CAT_COLORS = {"NEW FEATURE": "#00dd88", "IMPROVEMENT": GOLD_LT, "BUG FIX": "#cc6644"}
                    for cat, items in changes.items():
                        ctk.CTkLabel(news, text=f"    {cat}",
                                     font=("Segoe UI", 11, "bold"),
                                     text_color=CAT_COLORS.get(cat, DIM2),
                                     anchor="w").pack(fill="x", padx=20, pady=(4,0))
                        for item in items:
                            ctk.CTkLabel(news, text=f"      •  {item}", font=("Segoe UI",13),
                                         text_color=TEXT, anchor="w", wraplength=800).pack(fill="x", padx=20, pady=1)
                else:
                    for ch in changes:
                        ctk.CTkLabel(news,text=f"    •  {ch}",font=("Segoe UI",13),
                                     text_color=TEXT,anchor="w",wraplength=800).pack(fill="x",padx=20,pady=2)
                ctk.CTkFrame(news,fg_color=BG5,height=1).pack(fill="x",padx=20,pady=6)
        ctk.CTkFrame(news,height=8,fg_color="transparent").pack()
        ctk.CTkFrame(scroll,fg_color=GOLD_DK,height=1).pack(fill="x",padx=60,pady=(8,20))

    # ═══════════════════════════════════════════════════════════════════════════
    # LOG ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_log(self):
        page=ctk.CTkFrame(self._body,fg_color=BG,corner_radius=0)
        self._pages["Log Analysis"]=page
        top=ctk.CTkFrame(page,fg_color=BG2,height=54,corner_radius=0); top.pack(fill="x"); top.pack_propagate(False)
        ctk.CTkFrame(top,fg_color=GOLD_DK,height=1,corner_radius=0).place(relx=0,rely=1.0,relwidth=1.0,anchor="sw")
        gold_btn(top,"⟳  LOAD LOGS",self._load_logs,w=155,h=36).pack(side="left",padx=10,pady=9)
        self._path_lbl(top).pack(side="left",padx=4)
        ctk.CTkButton(top,text="…",width=32,height=30,fg_color=BG4,border_color=BORDER,border_width=1,command=self._set_path).pack(side="left")

        body=ctk.CTkFrame(page,fg_color=BG,corner_radius=0); body.pack(fill="both",expand=True,padx=6,pady=6)
        body.columnconfigure(1,weight=1); body.rowconfigure(0,weight=1)

        # Left — activities
        left=ctk.CTkFrame(body,fg_color=BG2,width=245,border_width=1,border_color=BORDER,corner_radius=4)
        left.grid(row=0,column=0,sticky="nsew",padx=(0,6)); left.pack_propagate(False)
        ctk.CTkLabel(left,text="  ✦  Activities",font=F_HEAD,text_color=GOLD).pack(pady=(12,4),anchor="w")
        ctk.CTkFrame(left,fg_color=GOLD_DK,height=1).pack(fill="x",padx=8,pady=(0,6))
        self._act_tv=ttk.Treeview(left,show="tree",selectmode="browse")
        self._act_tv.pack(fill="both",expand=True,padx=4,pady=(0,4))
        self._style_tv(); self._fill_act_tree()
        self._act_tv.bind("<<TreeviewSelect>>",self._on_act)

        # Right
        right=ctk.CTkFrame(body,fg_color=BG2,border_width=1,border_color=BORDER,corner_radius=4)
        right.grid(row=0,column=1,sticky="nsew")

        frow=ctk.CTkFrame(right,fg_color=BG3,height=48,corner_radius=0); frow.pack(fill="x")
        self._get_from,self._get_to=date_row(frow,self._refresh,self._all_time_log)
        dim_btn(frow,"🗑 Delete",self._delete_selected,w=95).pack(side="right",padx=2)
        dim_btn(frow,"Export CSV",self._bulk_csv,w=105).pack(side="right",padx=2)
        dim_btn(frow,"Copy Discord",self._bulk_discord,w=118).pack(side="right",padx=4)

        self._char_row=ctk.CTkFrame(right,fg_color=BG2,height=42); self._char_row.pack(fill="x",padx=6,pady=(6,0))
        self._canvas,self._inner,_=make_scrollable(right)
        self._refresh()

    def _all_time_log(self): self._refresh(ignore_dates=True)

    def _style_tv(self):
        s=ttk.Style(); s.theme_use("clam")
        s.configure("Treeview",background=BG2,foreground=TEXT,fieldbackground=BG2,
                    borderwidth=0,rowheight=28,font=F_BODY)
        s.configure("Treeview.Heading",background=BG3,foreground=GOLD)
        s.map("Treeview",background=[("selected",ACCENT)])

    def _fill_act_tree(self):
        tv=self._act_tv; tv.delete(*tv.get_children())
        # Load bonus icons once — stored on self to prevent garbage collection
        if not hasattr(self, "_tree_bonus_photos") or not self._tree_bonus_photos:
            self._tree_bonus_photos = {}
            for btype, fname in self.BONUS_ICONS.items():
                ph = make_photo(fname, (14,14), transparent=True)
                if ph:
                    self._tree_bonus_photos[btype] = ph
        tv.insert("","end",iid="All",        text="  ◆  All")
        tv.insert("","end",iid="Boating",    text="  ⚓  Boating")
        tv.insert("","end",iid="Harvesting", text="  🌲  Harvesting")
        dn=tv.insert("","end",iid="Dungeon",text="  ⚔  Dungeon",open=False)
        current_bonuses = self._get_current_bonuses()
        seen={}
        for d in self.dung_data.get("dungeons",[]):
            name=d["name"]; base=re.sub(r'\s+Lv-\d+$','',name).strip()
            if base not in seen:
                bonus = None
                for k,v in current_bonuses.items():
                    if k.lower() in base.lower() or base.lower() in k.lower():
                        bonus = v; break
                btype = bonus.get("type","") if bonus else ""
                bonus_txt = f"  {bonus.get('value','')} {bonus.get('label','')}" if bonus else ""
                img = self._tree_bonus_photos.get(btype) if btype else None
                seen[base]=tv.insert(dn,"end",iid=f"db_{base}",
                                     text=f"   {base}{bonus_txt}",
                                     image=img if img else "",
                                     open=False)
            tv.insert(seen[base],"end",iid=f"dl_{name}",text=f"        {name}")
        wn=tv.insert("","end",iid="Wilderness",text="  🌿  Wilderness",open=False)
        tv.insert(wn,"end",iid="wild_global",text="   ◆  Global")
        tv.insert(wn,"end",iid="wild_global",text="   ◆  Global")

    def _on_act(self,_):
        sel=self._act_tv.selection()
        if sel: self._act_f=sel[0]; self._refresh()

    def _filtered(self,ignore_dates=False):
        ss=list(self.sessions); f=self._act_f
        if   f=="Boating":      ss=[s for s in ss if "Boating"  in s.get("type","")]
        elif f=="Harvesting":   ss=[s for s in ss if "Harvest"  in s.get("type","")]
        elif f.startswith("dl_"): nm=f[3:];   ss=[s for s in ss if s.get("location","")==nm]
        elif f.startswith("db_"): base=f[3:]; ss=[s for s in ss if re.sub(r'\s+Lv-\d+$','',s.get("location","")).strip()==base]
        elif f=="Dungeon":      ss=[s for s in ss if "Creature Farming" in s.get("type","") or s.get("location")]
        elif f=="wild_global":  ss=[s for s in ss if not s.get("location") and "Boating" not in s.get("type","") and "Harvest" not in s.get("type","")]
        elif f=="Wilderness":   ss=[s for s in ss if not s.get("location") and "Boating" not in s.get("type","") and "Harvest" not in s.get("type","")]
        if self._char_f!="All": ss=[s for s in ss if s.get("player","")==self._char_f]
        if not ignore_dates:
            try:
                ft=self._get_from()
                if ft: fd=datetime.strptime(ft,"%Y-%m-%d"); ss=[s for s in ss if s.get("start") and s["start"]>=fd]
            except: pass
            try:
                tt=self._get_to()
                if tt: td=datetime.strptime(tt,"%Y-%m-%d")+timedelta(days=1); ss=[s for s in ss if s.get("start") and s["start"]<td]
            except: pass
        # Sort
        if self._sort_col:
            key_fn = {
                "player":   lambda s: s.get("player",""),
                "type":     lambda s: type_display(s),
                "date":     lambda s: s.get("start") or datetime.min,
                "dur":      lambda s: dur_min(s),
                "golds":    lambda s: s_gold(s),
                "doubloons":lambda s: s_doub(s),
                "rare":     lambda s: s_rare(s),
                "junk":     lambda s: s_junk(s),
                "harvest":  lambda s: s_harvest(s),
                "exp":      lambda s: s_exp(s),
            }.get(self._sort_col)
            if key_fn:
                ss=sorted(ss,key=key_fn,reverse=self._sort_rev)
        return ss

    def _refresh(self,ignore_dates=False):
        for w in self._char_row.winfo_children(): w.destroy()
        players=sorted(set(s.get("player","") for s in self.sessions if s.get("player","")))
        for name in ["All"]+players:
            sel=(name==self._char_f)
            ctk.CTkButton(self._char_row,text=name,width=95,height=30,
                          fg_color=ACCENT2 if sel else "transparent",
                          text_color=GOLD_LT if sel else DIM2,
                          hover_color=BG4,corner_radius=4,font=F_BODY,
                          border_width=1 if sel else 0,border_color=BORDER,
                          command=lambda n=name:self._set_char(n)).pack(side="left",padx=2,pady=5)
        for w in self._inner.winfo_children(): w.destroy()
        self._sel={}
        ss=self._filtered(ignore_dates=ignore_dates)
        self._draw_header()
        for i,s in enumerate(ss): self._draw_row(i,s)

    def _set_char(self,n): self._char_f=n; self._refresh()
    def _sort_by(self, col):
        if self._sort_col==col: self._sort_rev=not self._sort_rev
        else: self._sort_col=col; self._sort_rev=False
        self._refresh()

    # Column definitions: (key, label, icon_file, width)
    # (key, label, icon, width)
    # GAP=4 between each column — must be the same in header AND rows
    COL_GAP = 4
    COLS=[
        ("",         "",           None,                               40),
        ("player",   "Player",     "woodenshield.png",                110),
        ("type",     "Type",       "tinkering_globe.png",             165),
        ("date",     "Date",       "carpentrycraftingmanual.png",     115),
        ("dur",      "Dur.",       "tinkering_clock.png",              68),
        ("golds",    "Golds",      "goldpile.png",                    105),
        ("doubloons","Doubloons",  "doubloons1.png",                  115),
        ("rare",     "Rare",       "arcanescroll1.png",                80),
        ("bonus",    "Bonus",      "bonus_experience.png",             90),
        ("harvest",  "Harvest",    "hatchetiron1.png",                 95),
        ("exp",      "Exp",        "chromaticcore1.png",              110),
    ]

    def _draw_header(self):
        hdr=ctk.CTkFrame(self._inner,fg_color=BG3,height=24,corner_radius=0); hdr.pack(fill="x",pady=(0,0))
        ctk.CTkFrame(hdr,fg_color=GOLD_DK,height=1).place(relx=0,rely=0,relwidth=1.0)
        g=self.COL_GAP; w0=self.COLS[0][3]
        ctk.CTkFrame(hdr,fg_color="transparent",width=w0,height=24).pack(side="left",padx=(g,0))
        cells=[]
        for key,lbl,ico_file,w in self.COLS[1:]:
            cell=ctk.CTkFrame(hdr,fg_color="transparent",width=w,height=24)
            cell.pack(side="left",padx=(g,0)); cell.pack_propagate(False)
            sort_arrow=" ▼" if self._sort_col==key and self._sort_rev else " ▲" if self._sort_col==key else ""
            inner=ctk.CTkFrame(cell,fg_color="transparent"); inner.place(relx=0.5,rely=0.5,anchor="center")
            if ico_file:
                ico_ph=icon(ico_file,(14,14))
                if ico_ph:
                    ctk.CTkLabel(inner,image=ico_ph,text="",fg_color="transparent").pack(side="left",padx=(0,2))
            ctk.CTkButton(inner,text=f"{lbl}{sort_arrow}",
                          width=w-20,height=22,fg_color="transparent",
                          text_color=GOLD,hover_color=BG4,font=F_BODY_B,
                          anchor="center",command=lambda k=key:self._sort_by(k)).pack(side="left")
            cells.append(cell)
        ctk.CTkFrame(hdr,fg_color=GOLD_DK,height=1).place(relx=0,rely=1.0,relwidth=1.0,anchor="sw")
        # Draw separators after layout is computed using real widget positions
        def _draw_seps(h=hdr, cs=cells):
            h.update_idletasks()
            for cell in cs:
                x = cell.winfo_x()
                tk.Frame(h, bg="#303030", width=1, height=16).place(x=x-1, y=4)
            # Right border after last cell
            last = cs[-1]
            tk.Frame(h, bg="#303030", width=1, height=16).place(
                x=last.winfo_x()+last.winfo_width(), y=4)
        hdr.after(50, _draw_seps)

    def _draw_row(self,idx,s):
        mins=dur_min(s); g,d,r,j,h,e=s_gold(s),s_doub(s),s_rare(s),s_junk(s),s_harvest(s),s_exp(s)
        stype=type_display(s); dt=session_date(s); bg=ROW_A if idx%2==0 else ROW_B
        outer=ctk.CTkFrame(self._inner,fg_color=BG,corner_radius=0); outer.pack(fill="x",pady=1)
        row=ctk.CTkFrame(outer,fg_color=bg,corner_radius=3); row.pack(fill="x")
        var=tk.BooleanVar(); self._sel[id(s)]=(var,s)
        g=self.COL_GAP; w0=self.COLS[0][3]
        ctk.CTkCheckBox(row,variable=var,text="",width=w0,height=28,
                        checkbox_width=16,checkbox_height=16,
                        checkmark_color=GOLD,fg_color=ACCENT2,border_color=BORDER).pack(side="left",padx=(g,0))
        # Get bonus for this session
        sess_bonus = self._get_bonus_for_session(s)
        bonus_txt = f"{sess_bonus.get('value','')}\n{sess_bonus.get('label','')}" if sess_bonus else "—"
        bonus_type = sess_bonus.get("type","") if sess_bonus else ""
        vals=[
            (s.get("player","?"), 110, False),
            (stype,               165, True),
            (dt,                  115, False),
            (fmt_dur(mins),        68, False),
            (f"{g:,}\n({rate(g,mins)})",   105, False),
            (f"{d:,}\n({rate(d,mins)})",   115, False),
            (f"{r}\n({rate(r,mins)})",      80, False),
            (bonus_txt,            90, False),
            (f"{h:,}\n({rate(h,mins)})",    95, False),
            (f"{e:,.0f}\n({rate(e,mins)})",110, False),
        ]
        for i,(text,cw,wrap) in enumerate(vals):
            lbl = ctk.CTkLabel(row,text=text,width=cw,text_color=TEXT,font=F_BODY,
                         justify="center",
                         wraplength=cw-4 if wrap else 0)
            lbl.pack(side="left",padx=(g,0),pady=2)
            # Add bonus icon tooltip
            if i==7 and sess_bonus and bonus_type in self.BONUS_ICONS:
                bph = make_photo(self.BONUS_ICONS[bonus_type],(16,16),transparent=True)
                if bph:
                    self._photos.append(bph)
                    self._add_tooltip(lbl, f"{sess_bonus.get('label','')} {sess_bonus.get('value','')}")
        eb=ctk.CTkButton(row,text="▶",width=30,height=30,fg_color="transparent",text_color=DIM2,hover_color=BG4,font=F_BODY)
        eb.pack(side="right",padx=6)
        detail=ctk.CTkFrame(outer,fg_color=BG,corner_radius=0); state=[False]
        # Spacer shown when detail is open
        spacer=ctk.CTkFrame(outer,fg_color=BG3,height=3,corner_radius=0)
        def toggle(df=detail,st=state,btn=eb,sess=s,sp=spacer):
            if st[0]:
                df.pack_forget(); sp.pack_forget()
                btn.configure(text="▶"); st[0]=False
            else:
                df.pack(fill="x",pady=(1,0)); sp.pack(fill="x")
                btn.configure(text="▼"); st[0]=True
                if not df.winfo_children(): self._populate_detail(df,sess)
        eb.configure(command=toggle)

    def _populate_detail(self,frame,s):
        brow=ctk.CTkFrame(frame,fg_color="transparent",height=42); brow.pack(fill="x",pady=(4,2),padx=8)
        dim_btn(brow,"▼ Expand All",  lambda:self._all_cats(frame,True), w=120).pack(side="left",padx=4)
        dim_btn(brow,"▲ Collapse All",lambda:self._all_cats(frame,False),w=125).pack(side="left",padx=2)
        dim_btn(brow,"💾 Export CSV",  lambda:self._export_csv([s]),      w=115).pack(side="right",padx=4)
        dim_btn(brow,"Discord 📋",    lambda:self._copy_discord([s]),    w=115).pack(side="right",padx=2)

        loots=s.get("loots",{}); all_cats=sorted(loots.keys())
        if s.get("aspects_gained"): all_cats.append("__xp__")

        # 3-col grid, centered, gold-bordered cards, independent sizing
        center=ctk.CTkFrame(frame,fg_color="transparent"); center.pack(pady=6,padx=16)
        for i in range(3): center.columnconfigure(i,weight=1,uniform="cat")

        cats=[]; col=0; row_idx=0
        for cat in all_cats:
            card_border=ctk.CTkFrame(center,fg_color=GOLD_DK,corner_radius=5)
            card_border.grid(row=row_idx,column=col,sticky="new",padx=5,pady=4)
            # Each card is independent — no shared height
            card=ctk.CTkFrame(card_border,fg_color=BG3,corner_radius=4)
            card.pack(fill="x",padx=1,pady=1)
            col+=1
            if col>2: col=0; row_idx+=1

            icon_txt=CAT_ICONS.get(cat,"📦")
            if cat=="__xp__": cat_title=f"{icon_txt} Experience"; total_text=f"{s_exp(s):,.0f} xp"
            else: cat_title=f"{icon_txt} {cat}"; total_text=f"{sum(loots[cat].values()):,}"

            hdr=ctk.CTkFrame(card,fg_color=DETAIL_CH,corner_radius=3)
            hdr.pack(fill="x",padx=2,pady=(2,0))
            arr=ctk.CTkLabel(hdr,text="▶",width=20,text_color=GOLD,font=F_SMALL); arr.pack(side="left",padx=4,pady=4)
            ctk.CTkLabel(hdr,text=cat_title,text_color=GOLD_LT,font=F_SMALL_B).pack(side="left",pady=4)
            ctk.CTkLabel(hdr,text=f" ({total_text})",text_color=DIM2,font=F_SMALL).pack(side="left")

            # Items frame — separate from card, expands independently
            itf=ctk.CTkFrame(card,fg_color="transparent",corner_radius=0); ost=[False]

            if cat=="__xp__":
                for asp,gained in sorted(s.get("aspects_gained",{}).items()):
                    rf=ctk.CTkFrame(itf,fg_color="transparent"); rf.pack(fill="x",padx=8,pady=1)
                    ctk.CTkLabel(rf,text=asp,text_color=ASPECT_COLORS.get(asp,TEXT),font=F_SMALL,anchor="w").pack(side="left")
                    ctk.CTkLabel(rf,text=f"{gained:,.1f}xp",text_color=TEXT,font=F_SMALL,anchor="e").pack(side="right",padx=2)
            else:
                for item,qty in sorted(loots[cat].items()):
                    rf=ctk.CTkFrame(itf,fg_color="transparent"); rf.pack(fill="x",padx=8,pady=1)
                    ctk.CTkLabel(rf,text=item,text_color=TEXT,font=F_SMALL,anchor="w").pack(side="left")
                    ctk.CTkLabel(rf,text=f"×{qty:,}",text_color=GOLD_LT,font=F_SMALL_B,anchor="e").pack(side="right",padx=2)

            def tog(a=arr,i=itf,o=ost,c=card):
                if o[0]: i.pack_forget(); a.configure(text="▶"); o[0]=False
                else: i.pack(fill="x",padx=2,pady=(0,4)); a.configure(text="▼"); o[0]=True
            hdr.bind("<Button-1>",lambda e,t=tog:t()); arr.bind("<Button-1>",lambda e,t=tog:t())
            cats.append((ost,itf,arr))
        frame._cats=cats

    def _all_cats(self,frame,expand):
        if not hasattr(frame,"_cats"): return
        for ost,itf,arr in frame._cats:
            if expand and not ost[0]: itf.pack(fill="x",padx=2,pady=(0,4)); arr.configure(text="▼"); ost[0]=True
            elif not expand and ost[0]: itf.pack_forget(); arr.configure(text="▶"); ost[0]=False

    # ── Delete ─────────────────────────────────────────────────────────────────
    def _delete_selected(self):
        sel=self._selected()
        if not sel: messagebox.showwarning("Nothing selected","Select sessions first."); return
        choice=messagebox.askquestion("Delete sessions",
            f"Delete {len(sel)} session(s)?\n\n"
            "YES = This session only (can reload from logs)\n"
            "NO = Permanently (won't reload)",icon="warning")
        if choice=="yes":
            ids=set(id(s) for s in sel)
            self.sessions=[s for s in self.sessions if id(s) not in ids]
            self._refresh()
        else:
            if messagebox.askyesno("Confirm permanent delete",f"Permanently delete {len(sel)} session(s)?",icon="warning"):
                to_del=set(s.get("start","") for s in sel)
                self.sessions=[s for s in self.sessions if s.get("start","") not in to_del]
                self.sess_db["sessions"]=self._ser_sess(self.sessions)
                save_json(SESSIONS_F,self.sess_db); self._refresh()

    # ── Load logs ──────────────────────────────────────────────────────────────
    def _load_logs(self):
        root=self.settings.get("uo_root_path","")
        if not root: self._first_run(); return
        log_dir=Path(root)/"ClassicUO"/"Data"/"Client"/"JournalLogs"
        if not log_dir.exists(): messagebox.showerror("Error",f"Log folder not found:\n{log_dir}"); return
        files=sorted(log_dir.glob("*_journal.txt"))
        if not files: messagebox.showinfo("No logs","No journal log files found."); return
        modal=LoadingModal(self); self.update_idletasks()
        def progress_cb(done,total,fname):
            self.after(0,lambda:modal.update_progress(done,total,fname))
        def do_load():
            known=set(self.sess_db.get("known_files",[]))
            new_s,new_x=parse_logs(files,self.dung_data,self.wild_data,known,progress_cb)
            self.sessions.extend(new_s); self.xp_events.extend(new_x)
            self.sess_db["known_files"]=list(known)
            self.sess_db["sessions"]=self._ser_sess(self.sessions)
            save_json(SESSIONS_F,self.sess_db)
            self.xp_db["events"]=self._ser_xp(self.xp_events)
            save_json(XP_F,self.xp_db)
            self.after(0,lambda:self._load_done(modal,len(new_s),len(files)))
        threading.Thread(target=do_load,daemon=True).start()

    def _load_done(self,modal,new_s,total):
        try: modal.destroy()
        except: pass
        self._refresh()
        messagebox.showinfo("Done",f"Loaded {new_s} new session(s) from {total} log file(s).")

    def _selected(self): return [s for (var,s) in self._sel.values() if var.get()]

    def _bulk_csv(self):
        sel=self._selected()
        if not sel: messagebox.showwarning("Nothing selected","Select sessions first."); return
        self._export_csv(sel)

    def _bulk_discord(self):
        sel=self._selected()
        if not sel: messagebox.showwarning("Nothing selected","Select sessions first."); return
        self._copy_discord(sel)

    def _export_csv(self,sessions):
        path=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV","*.csv")],title="Save CSV")
        if not path: return
        with open(path,"w",newline="",encoding="utf-8") as f:
            w=csv.writer(f)
            for i,s in enumerate(sessions):
                if i: w.writerow([]); w.writerow(["─"*40]); w.writerow([])
                mins=dur_min(s)
                for row in [["Session",i+1],["Player",s.get("player","")],["Type",type_display(s)],
                            ["Start",s["start"].strftime("%Y-%m-%d %H:%M") if s.get("start") else ""],
                            ["End",  s["end"].strftime("%Y-%m-%d %H:%M")   if s.get("end")   else ""],
                            ["Duration",f"{mins:.1f} min"]]: w.writerow(row)
                for lbl,fn in [("Golds",s_gold),("Doubloons",s_doub),("Rare",s_rare),("Harvest",s_harvest),("Exp",s_exp)]:
                    v=fn(s); w.writerow([lbl,v,"Rate",rate(v,mins)])
                w.writerow(["Junk",s_junk(s)]); w.writerow([])
                w.writerow(["Category","Item","Qty"])
                for cat in sorted(s.get("loots",{})):
                    for item,qty in sorted(s["loots"][cat].items()): w.writerow([cat,item,qty])
                for asp,gained in sorted(s.get("aspects_gained",{}).items()):
                    w.writerow(["Experience",f"{asp} Aspect",f"{gained:.1f}"])
        messagebox.showinfo("Saved",f"CSV saved:\n{path}")

    def _copy_discord(self,sessions):
        self.clipboard_clear(); self.clipboard_append(discord_text(sessions))
        messagebox.showinfo("Copied!",f"{len(sessions)} session(s) copied in Discord format.")

    # ═══════════════════════════════════════════════════════════════════════════
    # EXPERIENCE
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_xp(self):
        page=ctk.CTkFrame(self._body,fg_color=BG,corner_radius=0)
        self._pages["Experience"]=page
        fbar=ctk.CTkFrame(page,fg_color=BG2,height=54,corner_radius=0); fbar.pack(fill="x"); fbar.pack_propagate(False)
        ctk.CTkFrame(fbar,fg_color=GOLD_DK,height=1,corner_radius=0).place(relx=0,rely=1.0,relwidth=1.0,anchor="sw")
        self._xget_from,self._xget_to=date_row(fbar,self._refresh_xp,self._all_time_xp)
        ctk.CTkLabel(fbar,text="  View:",text_color=DIM2,font=F_BODY).pack(side="left",padx=(16,4))
        self._xp_view=tk.StringVar(value="month")
        for label,val in [("Monthly","month"),("Daily","day"),("Hourly","hour")]:
            ctk.CTkRadioButton(fbar,text=label,variable=self._xp_view,value=val,
                               font=F_SMALL,text_color=TEXT,fg_color=GOLD,hover_color=GOLD_LT,
                               command=self._draw_xp).pack(side="left",padx=6)
        ctk.CTkLabel(fbar,text="  Character:",text_color=DIM2,font=F_BODY).pack(side="left",padx=(16,4))
        self._xp_cbar=ctk.CTkFrame(fbar,fg_color="transparent"); self._xp_cbar.pack(side="left")
        self._xp_chars=set()
        self._xp_chart=ctk.CTkFrame(page,fg_color=BG); self._xp_chart.pack(fill="both",expand=True,padx=8,pady=8)
        tbl_wrap=ctk.CTkFrame(page,fg_color="transparent"); tbl_wrap.pack(fill="x",pady=(0,8))
        self._xp_table=ctk.CTkScrollableFrame(tbl_wrap,fg_color=BG2,height=190,
                                               border_width=1,border_color=BORDER,width=940)
        self._xp_table.pack(anchor="center")
        self._refresh_xp()

    def _all_time_xp(self):
        # Select all characters before drawing
        players=sorted(set(e["player"] for e in self.xp_events if e.get("player")))
        self._xp_chars=set(players)
        self._refresh_xp_chars()
        self._draw_xp(ignore_dates=True)

    def _refresh_xp_chars(self):
        for w in self._xp_cbar.winfo_children(): w.destroy()
        players=sorted(set(e["player"] for e in self.xp_events if e.get("player")))
        for p in players:
            sel=p in self._xp_chars
            ctk.CTkButton(self._xp_cbar,text=p,width=95,height=30,
                          fg_color=GOLD if sel else BG4,text_color="#050505" if sel else DIM2,
                          hover_color=GOLD_LT,corner_radius=4,font=F_BODY,
                          border_width=1,border_color=BORDER,
                          command=lambda n=p:self._tog_xp(n)).pack(side="left",padx=2)

    def _refresh_xp(self):
        for w in self._xp_cbar.winfo_children(): w.destroy()
        players=sorted(set(e["player"] for e in self.xp_events if e.get("player")))
        if not self._xp_chars: self._xp_chars=set(players)
        for p in players:
            sel=p in self._xp_chars
            ctk.CTkButton(self._xp_cbar,text=p,width=95,height=30,
                          fg_color=GOLD if sel else BG4,text_color="#050505" if sel else DIM2,
                          hover_color=GOLD_LT,corner_radius=4,font=F_BODY,
                          border_width=1,border_color=BORDER,
                          command=lambda n=p:self._tog_xp(n)).pack(side="left",padx=2)
        self._draw_xp()

    def _tog_xp(self,n): self._xp_chars^={n}; self._refresh_xp()

    def _draw_xp(self,ignore_dates=False):
        for w in self._xp_chart.winfo_children(): w.destroy()
        for w in self._xp_table.winfo_children(): w.destroy()
        ev=list(self.xp_events)
        if not ignore_dates:
            try:
                ft=self._xget_from()
                if ft: fd=datetime.strptime(ft,"%Y-%m-%d"); ev=[e for e in ev if e["ts"]>=fd]
            except: pass
            try:
                tt=self._xget_to()
                if tt: td=datetime.strptime(tt,"%Y-%m-%d")+timedelta(days=1); ev=[e for e in ev if e["ts"]<td]
            except: pass
        ev=[e for e in ev if e.get("player","") in self._xp_chars]
        if not ev:
            ctk.CTkLabel(self._xp_chart,text="No XP data for the selected filters.",text_color=DIM,font=F_HEAD).pack(expand=True); return

        view=self._xp_view.get()
        def bk(ts):
            if view=="month": return ts.strftime("%b %Y")
            if view=="day":   return ts.strftime("%Y-%m-%d")
            return ts.strftime("%Y-%m-%d %Hh")
        def sk(k):
            if view=="month": return datetime.strptime(k,"%b %Y")
            if view=="day":   return datetime.strptime(k,"%Y-%m-%d")
            return datetime.strptime(k,"%Y-%m-%d %Hh")

        bucket_asp={}; last_xp={}
        for e in sorted(ev,key=lambda x:x["ts"]):
            key=(e["player"],e["aspect"]); b=bk(e["ts"]); asp=e["aspect"]
            bucket_asp.setdefault(b,{})
            if key in last_xp:
                pc,pm=last_xp[key]
                gained=(e["xp_cur"]-pc) if e["xp_cur"]>=pc else (pm-pc)+e["xp_cur"]
                bucket_asp[b][asp]=bucket_asp[b].get(asp,0)+max(0,gained)
            last_xp[key]=(e["xp_cur"],e["xp_max"])

        buckets=sorted(bucket_asp,key=sk); aspects=sorted({a for mv in bucket_asp.values() for a in mv})
        if not buckets: return
        if len(buckets)>60: buckets=buckets[-60:]

        fig,ax=plt.subplots(figsize=(max(8,len(buckets)*0.9),1.6))
        fig.patch.set_facecolor(BG); ax.set_facecolor(BG2)
        ax.tick_params(colors=TEXT,labelsize=8)
        for sp in ax.spines.values(): sp.set_edgecolor(BG3)
        x=np.arange(len(buckets)); bottoms=np.zeros(len(buckets))
        for asp in aspects:
            vals=np.array([bucket_asp[m].get(asp,0) for m in buckets])
            bars=ax.bar(x,vals,bottom=bottoms,label=asp,color=ASPECT_COLORS.get(asp,"#888"),width=0.72)
            for bar,val,bot in zip(bars,vals,bottoms):
                if val>0 and bar.get_height()>200:
                    ax.text(bar.get_x()+bar.get_width()/2, bot+bar.get_height()/2,
                            f"{asp}\n{int(val):,}", ha="center", va="center",
                            fontsize=5, color="black", fontweight="bold", clip_on=True)
            bottoms+=vals

        lbl_map={"month":"Monthly","day":"Daily","hour":"Hourly"}
        title=", ".join(sorted(self._xp_chars)) or "All"
        ax.set_title(f"XP ({lbl_map[view]}) — {title}",color=GOLD_LT,fontsize=10,pad=4)
        ax.set_xticks(x); ax.set_xticklabels(buckets,rotation=20 if view=="month" else 45,ha="right",color=TEXT,fontsize=7)
        ax.set_ylabel("XP",color=DIM,fontsize=7)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,p:f"{int(v):,}"))
        ax.legend(loc="upper left",fontsize=6,facecolor=BG3,labelcolor=TEXT,framealpha=0.9,ncol=5)
        plt.tight_layout(pad=0.3)
        FigureCanvasTkAgg(fig,master=self._xp_chart).get_tk_widget().pack(fill="both",expand=True)
        plt.close(fig)
        self._draw_xp_table(ev,last_xp)

    def _draw_xp_table(self,ev,last_xp):
        ctk.CTkLabel(self._xp_table,text="  ✦  Estimated Days to Next Level",
                     text_color=GOLD,font=F_TITLE).pack(anchor="w",padx=8,pady=(8,4))
        ctk.CTkFrame(self._xp_table,fg_color=GOLD_DK,height=1).pack(fill="x",padx=8,pady=(0,6))
        hdr=ctk.CTkFrame(self._xp_table,fg_color=BG3); hdr.pack(fill="x",padx=4,pady=(0,4))
        for col,w in [("Aspect",125),("Current XP",115),("Max XP",115),
                      ("Remaining",120),("Avg XP/day",115),("Est. Days",100)]:
            ctk.CTkLabel(hdr,text=col,width=w,text_color=GOLD,font=F_BODY_B).pack(side="left",padx=4,pady=4)
        seen={}
        for key,(xp_cur,xp_max) in sorted(last_xp.items()):
            _,asp=key
            if asp in seen: continue
            seen[asp]=True
            asp_ev=sorted([e for e in ev if e["aspect"]==asp],key=lambda x:x["ts"])
            total_g=0; prev={}
            for e in asp_ev:
                k2=(e["player"],e["aspect"])
                if k2 in prev:
                    pc,pm=prev[k2]
                    g=(e["xp_cur"]-pc) if e["xp_cur"]>=pc else (pm-pc)+e["xp_cur"]
                    total_g+=max(0,g)
                prev[k2]=(e["xp_cur"],e["xp_max"])
            span_days=max(1.0,(asp_ev[-1]["ts"]-asp_ev[0]["ts"]).total_seconds()/86400) if len(asp_ev)>=2 else 1.0
            avg_day=total_g/span_days; remaining=max(0,xp_max-xp_cur)
            est=remaining/avg_day if avg_day>0 else None
            color=ASPECT_COLORS.get(asp,TEXT)
            row=ctk.CTkFrame(self._xp_table,fg_color=BG2,corner_radius=4); row.pack(fill="x",padx=4,pady=1)
            for text,w in [(asp,125),(f"{xp_cur:,.1f}",115),(f"{xp_max:,.0f}",115),
                           (f"{remaining:,.1f}",120),(f"{avg_day:,.1f}",115),
                           (f"{est:.1f} days" if est else "—",100)]:
                ctk.CTkLabel(row,text=text,width=w,
                             text_color=color if text==asp else TEXT,
                             font=F_BODY_B if text==asp else F_BODY).pack(side="left",padx=4,pady=3)

    # ═══════════════════════════════════════════════════════════════════════════
    # HOW TO
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_howto(self):
        page=ctk.CTkFrame(self._body,fg_color=BG,corner_radius=0)
        self._pages["How To"]=page
        canvas,scroll,scroll_cb=make_scrollable(page,bg=BG)

        big=load_pil("O-MTBig.png",transparent=True)
        if big:
            ratio=big.width/big.height; big=big.resize((int(180*ratio),180),Image.LANCZOS)
            ph=ImageTk.PhotoImage(big); self._keep(ph)
            lbl=ctk.CTkLabel(scroll,image=ph,text="",fg_color=BG); lbl.pack(pady=(16,4))
        ctk.CTkFrame(scroll,fg_color=GOLD_DK,height=1).pack(fill="x",padx=30,pady=(4,8))

        def gold_panel(title,icon_t="✦"):
            wrap=ctk.CTkFrame(scroll,fg_color=BORDER,corner_radius=6); wrap.pack(fill="x",padx=30,pady=6)
            inner=ctk.CTkFrame(wrap,fg_color=BG3,corner_radius=5); inner.pack(fill="both",expand=True,padx=1,pady=1)
            hdr=ctk.CTkFrame(inner,fg_color=BG4,corner_radius=4); hdr.pack(fill="x",padx=4,pady=(4,0))
            ctk.CTkLabel(hdr,text=f"  {icon_t}  {title}",font=F_HEAD,text_color=GOLD_LT).pack(side="left",padx=8,pady=8)
            ctk.CTkFrame(inner,fg_color=GOLD_DK,height=1).pack(fill="x",padx=4,pady=(0,6))
            return inner

        def para(parent,text,color=TEXT):
            lbl=ctk.CTkLabel(parent,text=text,font=F_BODY,text_color=color,wraplength=900,justify="left",anchor="w")
            lbl.pack(fill="x",padx=14,pady=3)
            
        def bul(parent,items):
            for item in items:
                f=ctk.CTkFrame(parent,fg_color="transparent"); f.pack(fill="x",padx=14,pady=2)
                ctk.CTkLabel(f,text="  ◆",text_color=GOLD,font=F_BODY,width=28).pack(side="left")
                lbl=ctk.CTkLabel(f,text=item,font=F_BODY,text_color=TEXT,wraplength=860,justify="left",anchor="w")
                lbl.pack(side="left",fill="x"); 
        for sec in self.howto.get("sections",[]):
            p=gold_panel(sec.get("title",""),sec.get("icon","✦"))
            if sec.get("intro"): para(p,sec["intro"],DIM2)
            if sec.get("type") in ("bullets","mixed"): bul(p,sec.get("items",[]))
            if sec.get("outro"): para(p,sec["outro"],DIM2)

        try: START_CONTENT=(SCRIPTS_DIR/"OMT_START.razor").read_text(encoding="utf-8")
        except: START_CONTENT="(Script file not found: OMT_START.razor)"
        try: END_CONTENT=(SCRIPTS_DIR/"OMT_END.razor").read_text(encoding="utf-8")
        except: END_CONTENT="(Script file not found: OMT_END.razor)"

        p=gold_panel("Razor Scripts","⚙")
        para(p,"Place these scripts in your Razor macros folder.")
        for lbl_text,content,ico in [
            ("START Script — run on spot when you arrive at your farming location", START_CONTENT,"▶"),
            ("END Script — run at any safe place with loot bag full",                        END_CONTENT,  "■"),
        ]:
            sf=ctk.CTkFrame(p,fg_color=BG4,corner_radius=4,border_width=1,border_color=BORDER)
            sf.pack(fill="x",padx=10,pady=(8,4))
            ctk.CTkLabel(sf,text=f"  {ico}  {lbl_text}",font=F_BODY_B,text_color=GOLD_LT).pack(anchor="w",padx=8,pady=(6,2))
            box=ctk.CTkTextbox(sf,height=130,font=F_MONO,fg_color=BG2,text_color=TEXT,border_width=1,border_color=BORDER)
            box.pack(fill="x",padx=8,pady=(0,4)); box.insert("1.0",content); box.configure(state="disabled")
            # Red warning after END script only
            if "END Script" in lbl_text:
                warn=ctk.CTkLabel(sf,text="⚠  You must log out after running the END script for the log to be saved properly.",
                                  font=F_SMALL_B,text_color=RED,wraplength=860,justify="left",anchor="w")
                warn.pack(fill="x",padx=10,pady=(2,4))
            br=ctk.CTkFrame(sf,fg_color="transparent"); br.pack(fill="x",padx=8,pady=(0,8))
            def _copy(c=content): self.clipboard_clear(); self.clipboard_append(c); messagebox.showinfo("Copied","Copied!")
            def _dl(c=content,fn=lbl_text.split("—")[0].strip().replace(" ","_")+".razor"):
                path=filedialog.asksaveasfilename(defaultextension=".razor",initialfile=fn,filetypes=[("Razor Script","*.razor"),("All","*.*")])
                if path: Path(path).write_text(c,encoding="utf-8"); messagebox.showinfo("Saved",f"Saved:\n{path}")
            dim_btn(br,"📋  Copy",_copy,w=90).pack(side="left",padx=4)
            dim_btn(br,"💾  Download",_dl,w=115).pack(side="left",padx=4)

        st=self.howto.get("special_thanks",{})
        p=gold_panel("Special Thanks","❤")
        main_text=st.get("main","Thank you for using this program!")
        ctk.CTkLabel(p,text=main_text,font=("Palatino Linotype",15,"bold","italic"),
                     text_color=GOLD_LT,justify="center",wraplength=900).pack(pady=(10,6))
        ctk.CTkFrame(p,fg_color=GOLD_DK,height=1).pack(fill="x",padx=20,pady=4)
        if st.get("thanks"): para(p,st["thanks"],DIM2)
        if st.get("contact"): para(p,st["contact"],DIM2)
        ctk.CTkFrame(p,height=8,fg_color="transparent").pack()
        ctk.CTkLabel(p,text="Daping  ❤",font=("Palatino Linotype",16,"bold"),text_color=GOLD).pack(pady=(4,12))
        ctk.CTkFrame(scroll,fg_color=GOLD_DK,height=1).pack(fill="x",padx=30,pady=(12,4))
        ctk.CTkLabel(scroll,text=f"{APP_NAME}  ❤  by Daping",font=("Palatino Linotype",12,"italic"),text_color=DIM).pack(pady=(4,20))

    # ═══════════════════════════════════════════════════════════════════════════
    # SETTINGS
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_settings(self):
        page=ctk.CTkFrame(self._body,fg_color=BG,corner_radius=0)
        self._pages["Settings"]=page
        _,scroll,_=make_scrollable(page,bg=BG)

        def gold_panel(title,ico="✦"):
            wrap=ctk.CTkFrame(scroll,fg_color=BORDER,corner_radius=6); wrap.pack(fill="x",padx=80,pady=8)
            inner=ctk.CTkFrame(wrap,fg_color=BG3,corner_radius=5); inner.pack(fill="both",expand=True,padx=1,pady=1)
            hdr=ctk.CTkFrame(inner,fg_color=BG4,corner_radius=4); hdr.pack(fill="x",padx=4,pady=(4,0))
            ctk.CTkLabel(hdr,text=f"  {ico}  {title}",font=F_HEAD,text_color=GOLD_LT).pack(side="left",padx=8,pady=8)
            ctk.CTkFrame(inner,fg_color=GOLD_DK,height=1).pack(fill="x",padx=4,pady=(0,8))
            return inner

        ctk.CTkLabel(scroll,text="⚙  Settings",font=F_BIG,text_color=GOLD_LT).pack(pady=(30,4))
        ctk.CTkFrame(scroll,fg_color=GOLD_DK,height=1).pack(fill="x",padx=80,pady=(0,16))

        p=gold_panel("UO Outlands Folder","📁")
        path_row=ctk.CTkFrame(p,fg_color="transparent"); path_row.pack(fill="x",padx=14,pady=8)
        path_disp=ctk.CTkLabel(path_row,text=self.settings.get("uo_root_path","Not set"),
                               text_color=TEXT,font=F_MONO,wraplength=700,anchor="w")
        path_disp.pack(side="left",fill="x",expand=True)
        def change():
            self._set_path(); path_disp.configure(text=self.settings.get("uo_root_path","Not set"))
        gold_btn(path_row,"📁  Change Folder",change,w=165,h=34).pack(side="right",padx=8)

        p2=gold_panel("Reset","🔄")
        ctk.CTkLabel(p2,text="Reset clears all loaded sessions and XP data, and lets you reload everything from scratch.\nThe UO folder path is also cleared.",
                     font=F_BODY,text_color=DIM2,wraplength=800,justify="left").pack(padx=14,pady=(0,8),anchor="w")
        def do_reset():
            if not messagebox.askyesno("Reset","Clear ALL sessions and XP data?\nThis cannot be undone.",icon="warning"): return
            self.sessions=[]; self.xp_events=[]
            self.sess_db={"known_files":[],"sessions":[]}; self.xp_db={"events":[]}
            save_json(SESSIONS_F,self.sess_db); save_json(XP_F,self.xp_db)
            self.settings["uo_root_path"]=""; save_json(SETTINGS_F,self.settings)
            for lbl in getattr(self,"_path_labels",[]):
                try: lbl.configure(text="No folder selected")
                except: pass
            path_disp.configure(text="Not set"); self._refresh()
            messagebox.showinfo("Reset complete","All data cleared."); self._show("Home")
        ctk.CTkButton(p2,text="🔄  Reset Everything",width=190,height=40,
                      fg_color=RED,text_color=TEXT,hover_color="#aa2222",
                      font=F_BODY_B,corner_radius=5,command=do_reset).pack(padx=14,pady=(0,12))
        ctk.CTkFrame(scroll,fg_color=GOLD_DK,height=1).pack(fill="x",padx=80,pady=(16,20))

if __name__=="__main__":
    app = App()
    app.mainloop()
