"""
Outlands Multi Tracker
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
BONUS_SYMBOLS = {
    "sanctuary":  "🛡️",
    "challenger": "💀",
    "respawn":    "⚡",
    "gold_loot":  "💰",
    "experience": "⭐",
    "vendor":     "🪙",
    "crafting":   "🔨",
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

# ── Items to skip entirely (consumables, tools, non-loot) ─────────────────────
_SKIP_KEYWORDS = [
    # Identification wands
    "identification wand",
    # Potions (all levels: lesser, regular, greater, lethal etc.)
    "heal potion", "cure potion", "refresh potion", "agility potion",
    "strength potion", "explosion potion", "poison potion",
    "magic resist potion", "nightsight potion", "total refresh",
    "greater heal", "greater cure", "greater agility", "greater strength",
    "greater explosion", "greater magic resist", "lethal poison potion",
    "lesser heal", "lesser cure", "lesser poison", "lesser explosion",
    # Consumables
    "bandage", "veterinary supplies",
    # Tools
    "pickaxe", "shovel", "hatchet", "fishing pole", "sewing kit",
    "tinker's tools", "mortar and pestle", "scribe's pen", "scissors",
    " saw", "tongs", "skillet", "rolling pin", "smoothing plane",
    "scorp", "spyglass", "lockpick",
]

def should_skip_item(desc):
    """Return True if item should be excluded from loot tracking."""
    d = desc.lower().strip()
    # Skip identification wands
    if "identification wand" in d:
        return True
    # Skip exceptional crooks
    if "crook" in d and "exceptional" in d:
        return True
    # Skip all other keywords
    for kw in _SKIP_KEYWORDS:
        if kw in d:
            return True
    return False

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
        # Use filename only (not full path) so moving the folder doesn't break history
        fid=fpath.name
        if fid in known_ids: continue
        if fpath.stat().st_size == 0: continue  # Skip empty — game locks file while running
        sessions_before = len(sessions)
        # Don't mark as known yet — only mark after finding at least one complete session
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
                    if should_skip_item(iname): continue
                    cat=categorise_item(iname)
                    cur["loots"].setdefault(cat,{})
                    cur["loots"][cat][iname]=cur["loots"][cat].get(iname,0)+qty
            xp_m=re.search(r'\(([\w ]+?) Aspect ([\d,\.]+)/([\d,]+) xp\)',msg)
            if xp_m:
                asp=xp_m.group(1); xp_cur=float(xp_m.group(2).replace(",","")); xp_max=float(xp_m.group(3).replace(",",""))
                player=cur.get("player","")
                xp_events.append({"ts":ts,"player":player,"aspect":asp,"xp_cur":xp_cur,"xp_max":xp_max})
                asp_first.setdefault(asp,(xp_cur,xp_max))
                cur["aspects"][asp]=(xp_cur,xp_max,asp_first[asp])
            # Parse gold/doubloons from bank deposits (happen during session or after END)
            if author=="System":
                gm=re.search(r'You deposit ([\d,]+) gold into your bank',msg)
                if gm and cur:
                    amt=int(gm.group(1).replace(",",""))
                    cur["loots"].setdefault("Gold & Currency",{})
                    cur["loots"]["Gold & Currency"]["gold coins"]=cur["loots"]["Gold & Currency"].get("gold coins",0)+amt
                dm=re.search(r'You deposit ([\d,]+) doubloons into your bank',msg)
                if dm and cur:
                    amt=int(dm.group(1).replace(",",""))
                    cur["loots"].setdefault("Gold & Currency",{})
                    cur["loots"]["Gold & Currency"]["doubloons"]=cur["loots"]["Gold & Currency"].get("doubloons",0)+amt
            if is_razor and ("SESSION END" in msg or "SESSION : ENDING" in msg):
                cur["end"]=ts
                p=get_player(ts)
                if p: cur["player"]=p
                gained={}
                for asp,(cv,mx,(fv,fmx)) in cur["aspects"].items():
                    gained[asp]=(cv-fv) if cv>=fv else (fmx-fv)+cv
                cur["aspects_gained"]=gained; sessions.append(cur); cur=None; asp_first={}
        # Mark ALL non-empty files as known after processing.
        # Files with no OMT sessions won't be reparsed next time.
        # Only empty files (0 bytes, skipped above) stay unknown so they're retried.
        known_ids.add(fid)
        # But if THIS file produced new complete sessions, note it
        _ = len(sessions) > sessions_before  # sessions_before set above
    return sessions, xp_events

# ── Metrics ────────────────────────────────────────────────────────────────────
def dur_min(s):
    if s.get("end") and s.get("start"):
        secs=(s["end"]-s["start"]).total_seconds()
        return max(0.1, secs/60)  # min 0.1 to avoid division by zero
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

def download_update(download_url, progress_cb=None):
    """Download + pre-extract zip. Returns pre_extract_dir or None.
    Runs in background thread — app stays responsive during download."""
    import ssl, zipfile, shutil
    tmp_zip = BASE_DIR / "_update.zip"
    headers = {"User-Agent": "Mozilla/5.0 OutlandsMultiTracker"}
    if not download_url:
        raise ValueError("No download URL provided")
    try:
        if tmp_zip.exists(): tmp_zip.unlink()
    except Exception as e:
        raise RuntimeError(f"Cannot clean old zip: {e}")

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
    for verify in [False, True]:
        try:
            size = _try_download(download_url, tmp_zip, verify)
            if size == 0: raise RuntimeError("Downloaded file is empty")
            last_err = None; break
        except Exception as e:
            last_err = e
            try: tmp_zip.unlink(missing_ok=True)
            except: pass
    if last_err:
        raise RuntimeError(f"Download failed: {last_err}")
    if not zipfile.is_zipfile(str(tmp_zip)):
        try: tmp_zip.unlink(missing_ok=True)
        except: pass
        raise RuntimeError("Not a valid zip archive")

    # Pre-extract while app still running — eliminates extraction delay
    if progress_cb: progress_cb(0, 1, "Preparing...")
    pre_dir = BASE_DIR / "_update_pre"
    try:
        if pre_dir.exists(): shutil.rmtree(pre_dir, ignore_errors=True)
        pre_dir.mkdir()
        with zipfile.ZipFile(str(tmp_zip), "r") as z:
            z.extractall(pre_dir)
        return pre_dir
    except Exception as e:
        print(f"[UPDATE] Pre-extract failed: {e}")
        return None

def launch_updater(pre_dir=None):
    """Launch Updater.exe immediately. Call after download_update()."""
    updater_exe = BASE_DIR / "Updater.exe"
    tmp_zip     = BASE_DIR / "_update.zip"
    exe_name    = "OutlandsMultiTracker.exe"
    if not updater_exe.exists():
        raise FileNotFoundError(f"Updater.exe not found")
    args = [str(updater_exe), str(tmp_zip), str(BASE_DIR), exe_name]
    if pre_dir and pre_dir.exists():
        args += ["--pre-extracted", str(pre_dir)]
    subprocess.Popen(args, creationflags=subprocess.DETACHED_PROCESS,
                     close_fds=True, cwd=str(BASE_DIR))

def do_update(download_url, progress_cb=None):
    """Legacy wrapper — kept for compatibility."""
    pre_dir = download_update(download_url, progress_cb)
    if progress_cb: progress_cb(0, 1, "Launching installer...")
    launch_updater(pre_dir)
    return True



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
        """Return bonus dict for the current week. Fallback to most recent week."""
        if not self.bonuses_db:
            return {}
        today = datetime.utcnow().date()
        # ISO week key: "YYYY-WXX"
        week_key = today.strftime("%G-W%V")
        if week_key in self.bonuses_db:
            return self.bonuses_db[week_key]
        # Fallback: use the most recent available week
        try:
            latest_key = max(self.bonuses_db.keys())
            return self.bonuses_db[latest_key]
        except Exception:
            return {}

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
        """Show feedback modal directly in the app."""
        modal = tk.Toplevel(self)
        modal.title("Feedback")
        modal.configure(bg=BG)
        modal.resizable(False, False)
        modal.grab_set()
        modal.protocol("WM_DELETE_WINDOW", modal.destroy)
        w, h = 480, 520
        x = self.winfo_rootx() + (self.winfo_width()  - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        modal.geometry(f"{w}x{h}+{x}+{y}")

        # Header
        hdr = ctk.CTkFrame(modal, fg_color=BG2, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="⚔  O-MT Feedback",
                     font=("Georgia", 16, "bold"), text_color=GOLD_LT,
                     fg_color=BG2).pack(pady=(14,2))
        ctk.CTkLabel(hdr, text="Report a bug or share a suggestion",
                     font=F_SMALL, text_color=DIM2, fg_color=BG2).pack(pady=(0,12))
        ctk.CTkFrame(hdr, fg_color=GOLD_DK, height=1).pack(fill="x")

        scroll_frame = ctk.CTkScrollableFrame(modal, fg_color=BG, corner_radius=0)
        scroll_frame.pack(fill="both", expand=True, padx=16, pady=12)

        # Type selection
        ctk.CTkLabel(scroll_frame, text="Type", font=F_BODY, text_color=DIM2,
                     anchor="w").pack(fill="x", pady=(0,6))
        type_var = tk.StringVar(value="")
        type_row = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        type_row.pack(fill="x", pady=(0,12))
        type_btns = {}
        def select_type(t):
            type_var.set(t)
            for k, b in type_btns.items():
                b.configure(fg_color=GOLD if k==t else BG3,
                            text_color="#050505" if k==t else DIM2,
                            border_color=GOLD if k==t else BORDER)
        for i, (label, emoji) in enumerate([("Bug","🐛"), ("Suggestion","💡"), ("Other","📝")]):
            b = ctk.CTkButton(type_row, text=f"{emoji}  {label}", width=134, height=38,
                              fg_color=BG3, text_color=DIM2, hover_color=BG4,
                              border_width=1, border_color=BORDER, corner_radius=6,
                              font=F_BODY, command=lambda t=label: select_type(t))
            b.grid(row=0, column=i, padx=(0,6) if i<2 else 0)
            type_btns[label] = b

        # Description
        ctk.CTkLabel(scroll_frame, text="Description", font=F_BODY, text_color=DIM2,
                     anchor="w").pack(fill="x", pady=(0,6))
        desc_box = ctk.CTkTextbox(scroll_frame, height=110, font=F_BODY,
                                   fg_color=BG3, border_color=BORDER, border_width=1)
        desc_box.pack(fill="x", pady=(0,12))

        # Pseudo
        ctk.CTkLabel(scroll_frame, text="In-game name  (optional)", font=F_BODY,
                     text_color=DIM2, anchor="w").pack(fill="x", pady=(0,6))
        pseudo_entry = ctk.CTkEntry(scroll_frame, placeholder_text="Your character name",
                                    height=36, font=F_BODY)
        pseudo_entry.pack(fill="x", pady=(0,16))

        # Status label
        status_lbl = ctk.CTkLabel(scroll_frame, text="", font=F_SMALL,
                                   text_color=DIM2, fg_color="transparent")
        status_lbl.pack()

        def send():
            ftype   = type_var.get()
            version = APP_VERSION
            desc    = desc_box.get("1.0", "end").strip()
            pseudo  = pseudo_entry.get().strip() or "Anonymous"
            if not ftype: status_lbl.configure(text="⚠ Please select a type.", text_color="#cc4444"); return
            if not desc:  status_lbl.configure(text="⚠ Please add a description.", text_color="#cc4444"); return

            send_btn.configure(state="disabled", text="Sending...")
            status_lbl.configure(text="", text_color=DIM2)

            emojis = {"Bug":"🐛","Suggestion":"💡","Other":"📝"}
            colors = {"Bug":13395012,"Suggestion":13145898,"Other":5604556}
            import urllib.request as _ur, json as _json, ssl as _ssl
            payload = _json.dumps({"embeds":[{
                "title": f"{emojis.get(ftype,'📝')}  New Feedback — {ftype}",
                "description": desc,
                "color": colors.get(ftype, 8947848),
                "fields": [
                    {"name":"Version","value":version,"inline":True},
                    {"name":"Type",   "value":ftype,  "inline":True},
                    {"name":"Player", "value":pseudo, "inline":True}
                ],
                "footer":{"text":f"OMT Feedback • {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}"}
            }]}).encode()

            def do_send():
                try:
                    ctx = _ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = _ssl.CERT_NONE
                    req = _ur.Request(
                        "https://discord.com/api/webhooks/1510977027895984149/85LKfte18fOibmEbrLEo4OkLcVEvjR57NeTSlHywsKaluLAlzV92vrK4Oc4s0dp_RU1S",
                        data=payload,
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "OMT-Feedback/1.0"
                        },
                        method="POST")
                    with _ur.urlopen(req, timeout=10, context=ctx) as r:
                        ok = r.status in (200, 204, 201)
                    if ok:
                        self.after(0, lambda: (
                            status_lbl.configure(text="✓ Feedback sent! Thank you.", text_color="#80c080"),
                            send_btn.configure(state="disabled", text="Sent ✓",
                                               fg_color="#1a4a1a", text_color="#80c080")
                        ))
                    else:
                        self.after(0, lambda: (
                            status_lbl.configure(text="⚠ Error sending. Please try again.", text_color="#cc4444"),
                            send_btn.configure(state="normal", text="Send Feedback")
                        ))
                except Exception as e:
                    self.after(0, lambda err=str(e): (
                        status_lbl.configure(text=f"⚠ {err[:60]}", text_color="#cc4444"),
                        send_btn.configure(state="normal", text="Send Feedback")
                    ))
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
    # ── Floating update panel ──────────────────────────────────────────────────
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
            ("Guild",        "Guild",        "guild.png"),
            ("How To",       "How To",       "shepherdscrook.png"),
        ]
        for key, label, ico_name in tab_defs:
            b=nav_btn(nav, label, ico_name, lambda n=key: self._show(n))
            b.pack(side="left", padx=4, pady=8)
            self._tb[key]=b

        settings_btn=nav_btn(nav,"Settings","tinkering_tinkertools.png",lambda:self._show("Settings"))
        settings_btn.pack(side="right",padx=4,pady=8)
        self._tb["Settings"]=settings_btn

        feedback_btn=nav_btn(nav,"Feedback","feedback.png",self._open_feedback)
        feedback_btn.pack(side="right",padx=4,pady=8)

        ctk.CTkLabel(nav,text=f"v{APP_VERSION}",font=F_SMALL_B,text_color=GOLD_LT,fg_color=NAV_BG).pack(side="right",padx=4)

        self._body=ctk.CTkFrame(self,fg_color=BG,corner_radius=0)
        self._body.pack(fill="both",expand=True)
        self._build_home()
        self._build_log()
        self._build_xp()
        self._build_guild()
        self._build_howto()
        self._build_settings()
        self._show("Home")
        try: splash.destroy()
        except: pass
        self.deiconify()
        self.lift()
        self.focus_force()
        # Start Log Analysis on All / All Time
        self._act_f  = "All"
        self._char_f = "All"
        self.after(100, self._all_time_log)
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
        self._act_tv.bind("<Motion>", self._tree_tooltip_show)
        self._act_tv.bind("<Leave>",  self._tree_tooltip_hide)

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
        """Rebuild the activities tree. Safe to call multiple times."""
        if getattr(self, "_tree_building", False):
            return
        self._tree_building = True
        try:
            tv = self._act_tv
            tv.delete(*tv.get_children())
            # Load bonus icons once — 16x16, kept on self to prevent GC
            if not getattr(self, "_tree_bonus_photos", None):
                self._tree_bonus_photos = {}
                for btype, fname in self.BONUS_ICONS.items():
                    ph = make_photo(fname, (16,16), transparent=True)
                    if ph:
                        self._tree_bonus_photos[btype] = ph
            # Store bonus info for tooltips
            self._tree_bonus_map = {}  # iid -> (label, value)
            tv.insert("","end",iid="All",        text="   ◆   All")
            tv.insert("","end",iid="Boating",    text="  ⚓  Boating")
            tv.insert("","end",iid="Harvesting", text="  ⛏  Harvesting")
            dn = tv.insert("","end",iid="Dungeon", text="  ⚔  Dungeon", open=False)
            current_bonuses = self._get_current_bonuses()
            seen = {}
            for d in self.dung_data.get("dungeons",[]):
                name = d["name"]
                base = re.sub(r'\s+Lv-\d+$', '', name).strip()
                if base not in seen:
                    bonus = None
                    for k,v in current_bonuses.items():
                        if k.lower() in base.lower() or base.lower() in k.lower():
                            bonus = v; break
                    try:
                        bonus_val = float(bonus.get("value","0").replace("%","").replace("+","").strip()) if bonus else 0
                    except:
                        bonus_val = 0
                    btype = bonus.get("type","") if bonus else ""
                    is_type_indicator = btype in ("sanctuary","challenger")
                    has_symbol = bonus is not None and (bonus_val > 0 or is_type_indicator)
                    symbol = BONUS_SYMBOLS.get(btype,"") if has_symbol else ""
                    iid    = f"db_{base}"
                    label  = f"   {base}  {symbol}" if symbol else f"   {base}"
                    seen[base] = tv.insert(dn,"end",iid=iid,
                                           text=label,
                                           open=False)
                    if has_symbol:
                        tip_val = bonus.get("value","") if bonus_val > 0 else ""
                        self._tree_bonus_map[iid] = (bonus.get("label",""), tip_val)
                tv.insert(seen[base],"end",iid=f"dl_{name}",text=f"        {name}")
            wn = tv.insert("","end",iid="Wilderness", text="  🌿  Wilderness", open=False)
            tv.insert(wn,"end",iid="wild_global", text="   ◆  Global")
        except Exception as e:
            print(f"[TREE] _fill_act_tree error: {e}")
        finally:
            self._tree_building = False

    def _tree_tooltip_show(self, event):
        """Show bonus tooltip when hovering a dungeon row with a bonus."""
        try:
            tv = self._act_tv
            iid = tv.identify_row(event.y)
            bonus_map = getattr(self, "_tree_bonus_map", {})
            if iid in bonus_map:
                label, value = bonus_map[iid]
                tip = f"{label}  {value}"
                if not hasattr(self, "_tv_tip") or not self._tv_tip:
                    self._tv_tip = tk.Toplevel(self)
                    self._tv_tip.wm_overrideredirect(True)
                    self._tv_tip.attributes("-topmost", True)
                    self._tv_tip_lbl = tk.Label(self._tv_tip, background="#1a1a1a",
                                                foreground=GOLD_LT, font=F_SMALL,
                                                relief="solid", borderwidth=1, padx=6, pady=3)
                    self._tv_tip_lbl.pack()
                self._tv_tip_lbl.configure(text=tip)
                self._tv_tip.wm_geometry(f"+{event.x_root+14}+{event.y_root+6}")
                self._tv_tip.deiconify()
            else:
                self._tree_tooltip_hide(event)
        except Exception:
            pass

    def _tree_tooltip_hide(self, event):
        if hasattr(self, "_tv_tip") and self._tv_tip:
            try: self._tv_tip.withdraw()
            except: pass

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

    # Columns: (key, label, icon_file, width) — GAP=4 between each column in header AND rows
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
        mins=dur_min(s); gold,doub,rare,junk,harv,exp=s_gold(s),s_doub(s),s_rare(s),s_junk(s),s_harvest(s),s_exp(s)
        stype=type_display(s); dt=session_date(s); bg=ROW_A if idx%2==0 else ROW_B
        outer=ctk.CTkFrame(self._inner,fg_color=BG,corner_radius=0); outer.pack(fill="x",pady=1)
        row=ctk.CTkFrame(outer,fg_color=bg,corner_radius=3); row.pack(fill="x")
        var=tk.BooleanVar(); self._sel[id(s)]=(var,s)
        gap=self.COL_GAP; w0=self.COLS[0][3]
        ctk.CTkCheckBox(row,variable=var,text="",width=w0,height=28,
                        checkbox_width=16,checkbox_height=16,
                        checkmark_color=GOLD,fg_color=ACCENT2,border_color=BORDER).pack(side="left",padx=(gap,0))
        # Get bonus for this session
        sess_bonus = self._get_bonus_for_session(s)
        bonus_txt = f"{sess_bonus.get('value','')}\n{sess_bonus.get('label','')}" if sess_bonus else "—"
        bonus_type = sess_bonus.get("type","") if sess_bonus else ""
        # Pre-load bonus photo (32x32 for row display)
        bonus_photo = None
        if sess_bonus and bonus_type in self.BONUS_ICONS:
            key = (bonus_type, "row")
            if key not in getattr(self, "_row_bonus_photos", {}):
                if not hasattr(self, "_row_bonus_photos"):
                    self._row_bonus_photos = {}
                ph = make_photo(self.BONUS_ICONS[bonus_type], (32,32), transparent=True)
                if ph:
                    self._row_bonus_photos[key] = ph
            bonus_photo = getattr(self, "_row_bonus_photos", {}).get(key)

        vals=[
            (s.get("player","?"), 110, False),
            (stype,               165, True),
            (dt,                  115, False),
            (fmt_dur(mins),        68, False),
            (f"{gold:,}\n({rate(gold,mins)})",   105, False),
            (f"{doub:,}\n({rate(doub,mins)})",   115, False),
            (f"{rare}\n({rate(rare,mins)})",      80, False),
            (None,                 90, False),  # bonus — handled separately
            (f"{harv:,}\n({rate(harv,mins)})",    95, False),
            (f"{exp:,.0f}\n({rate(exp,mins)})",  110, False),
        ]
        for i,(text,cw,wrap) in enumerate(vals):
            if i == 7:
                # Bonus cell — icon if available, text fallback
                cell = ctk.CTkFrame(row, fg_color="transparent", width=cw, height=28)
                cell.pack(side="left", padx=(gap,0), pady=2)
                cell.pack_propagate(False)
                if bonus_photo and sess_bonus:
                    ico_lbl = ctk.CTkLabel(cell, image=bonus_photo, text="",
                                           fg_color="transparent", width=cw)
                    ico_lbl.pack(expand=True)
                    self._add_tooltip(ico_lbl, f"{sess_bonus.get('label','')}  {sess_bonus.get('value','')}")
                else:
                    ctk.CTkLabel(cell, text="—", width=cw, text_color=DIM2,
                                 font=F_BODY, justify="center").pack(expand=True)
            else:
                lbl = ctk.CTkLabel(row, text=text, width=cw, text_color=TEXT, font=F_BODY,
                                   justify="center", wraplength=cw-4 if wrap else 0)
                lbl.pack(side="left", padx=(gap,0), pady=2)
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
        modal=tk.Toplevel(self)
        modal.title("Delete Sessions")
        modal.resizable(False,False)
        modal.attributes("-topmost",True)
        modal.grab_set()
        modal.configure(bg=BG)
        modal.protocol("WM_DELETE_WINDOW", modal.destroy)
        modal.update_idletasks()
        w,h=360,160
        x=self.winfo_rootx()+(self.winfo_width()-w)//2
        y=self.winfo_rooty()+(self.winfo_height()-h)//2
        modal.geometry(f"{w}x{h}+{x}+{y}")
        ctk.CTkLabel(modal,text=f"Delete {len(sel)} session(s)?",
                     font=("Segoe UI",14,"bold"),text_color=TEXT,fg_color=BG).pack(pady=(20,4))
        ctk.CTkLabel(modal,text="This Session  —  removable by reloading logs\nPermanent  —  cannot be recovered",
                     font=("Segoe UI",11),text_color=DIM2,fg_color=BG,justify="center").pack(pady=(0,16))
        btn_row=ctk.CTkFrame(modal,fg_color=BG); btn_row.pack()
        result=[None]
        def do(r): result[0]=r; modal.destroy()
        ctk.CTkButton(btn_row,text="This Session",width=105,height=34,
                      fg_color=ACCENT2,text_color=TEXT,hover_color=BG4,
                      font=("Segoe UI",12),corner_radius=5,
                      command=lambda:do("session")).pack(side="left",padx=6)
        ctk.CTkButton(btn_row,text="Permanent",width=105,height=34,
                      fg_color="#8b2020",text_color="#ffffff",hover_color="#a03030",
                      font=("Segoe UI",12),corner_radius=5,
                      command=lambda:do("permanent")).pack(side="left",padx=6)
        ctk.CTkButton(btn_row,text="Cancel",width=85,height=34,
                      fg_color=BG3,text_color=DIM2,hover_color=BG4,
                      font=("Segoe UI",12),corner_radius=5,
                      command=lambda:do("cancel")).pack(side="left",padx=6)
        modal.wait_window()
        if result[0]=="session":
            ids=set(id(s) for s in sel)
            self.sessions=[s for s in self.sessions if id(s) not in ids]
            self._refresh()
        elif result[0]=="permanent":
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
            raw_known=self.sess_db.get("known_files",[])
            # Migrate: strip absolute paths to filename only
            known=set(Path(f).name if (os.sep in f or "/" in f) else f for f in raw_known)
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
        self._draw_xp(ignore_dates=True)

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

        # ── Chart sizing — minimum height for readability ────────────────────
        n_buckets = len(buckets)
        fig_w = max(10, n_buckets * 0.85)
        fig_h = 4.5
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=96)
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG2)

        # Spine and tick styling
        for sp in ax.spines.values(): sp.set_edgecolor(BG3)
        ax.tick_params(colors=TEXT, labelsize=8, length=3)
        ax.set_axisbelow(True)

        # Light dotted grid on Y — improves value reading
        ax.yaxis.grid(True, linestyle=":", linewidth=0.6, color="#333333", alpha=0.8)
        ax.xaxis.grid(False)

        x = np.arange(n_buckets)
        bottoms = np.zeros(n_buckets)

        # Store bar info for tooltip
        bar_data = []  # list of (bar_artist, asp_name, val) for tooltip

        for asp in aspects:
            vals = np.array([bucket_asp[m].get(asp, 0) for m in buckets])
            bars = ax.bar(x, vals, bottom=bottoms, label=asp,
                          color=ASPECT_COLORS.get(asp, "#888"),
                          width=0.78, edgecolor="none")
            for bar, val, bot in zip(bars, vals, bottoms):
                bar_data.append((bar, asp, val))
                if val > 0 and bar.get_height() > 300:
                    ax.text(bar.get_x() + bar.get_width() / 2,
                            bot + bar.get_height() / 2,
                            f"{asp}\n{int(val):,}",
                            ha="center", va="center",
                            fontsize=6, color="#000000",
                            fontweight="bold", clip_on=True)
            bottoms += vals

        lbl_map = {"month": "Monthly", "day": "Daily", "hour": "Hourly"}
        title = ", ".join(sorted(self._xp_chars)) or "All"
        ax.set_title(f"XP — {lbl_map[view]} — {title}",
                     color=GOLD_LT, fontsize=11, pad=8, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(buckets, rotation=45, ha="right", color=TEXT, fontsize=8)
        ax.set_ylabel("XP Gained", color=DIM, fontsize=9, labelpad=6)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{int(v):,}"))

        # Legend below chart — cleaner than inside
        legend = ax.legend(loc="upper center",
                           bbox_to_anchor=(0.5, -0.22),
                           ncol=min(len(aspects), 6),
                           fontsize=8,
                           facecolor=BG3,
                           labelcolor=TEXT,
                           framealpha=0.9,
                           edgecolor=BG3,
                           handlelength=1.2,
                           handleheight=0.8)

        plt.tight_layout(pad=0.5, rect=[0, 0.08, 1, 1])

        canvas = FigureCanvasTkAgg(fig, master=self._xp_chart)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill="both", expand=True)

        # ── Tooltip on hover ─────────────────────────────────────────────────
        tip_win = [None]
        tip_lbl = [None]

        def _on_motion(event):
            if event.inaxes != ax:
                _hide_tip()
                return
            for bar, asp, val in bar_data:
                if val <= 0: continue
                if bar.contains(event)[0]:
                    _show_tip(event, asp, val)
                    return
            _hide_tip()

        def _show_tip(event, asp, val):
            if tip_win[0] is None or not tip_win[0].winfo_exists():
                tip_win[0] = tk.Toplevel(self)
                tip_win[0].wm_overrideredirect(True)
                tip_win[0].attributes("-topmost", True)
                tip_lbl[0] = tk.Label(tip_win[0],
                                      background="#1a1a1a",
                                      foreground=ASPECT_COLORS.get(asp, GOLD_LT),
                                      font=("Segoe UI", 10, "bold"),
                                      relief="solid", borderwidth=1,
                                      padx=8, pady=4)
                tip_lbl[0].pack()
            else:
                tip_lbl[0].configure(foreground=ASPECT_COLORS.get(asp, GOLD_LT))
            tip_lbl[0].configure(text=f"{asp}  —  {int(val):,} XP")
            rx = canvas_widget.winfo_rootx() + int(event.x) + 14
            ry = canvas_widget.winfo_rooty() + int(canvas_widget.winfo_height() - event.y) - 20
            tip_win[0].wm_geometry(f"+{rx}+{ry}")
            tip_win[0].deiconify()

        def _hide_tip():
            if tip_win[0] and tip_win[0].winfo_exists():
                tip_win[0].withdraw()

        def _on_leave(event):
            _hide_tip()

        canvas.mpl_connect("motion_notify_event", _on_motion)
        canvas.mpl_connect("figure_leave_event", _on_leave)
        plt.close(fig)
        self._draw_xp_table(ev, last_xp)

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
    # GUILD
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_guild(self):
        page=ctk.CTkFrame(self._body,fg_color=BG,corner_radius=0)
        self._pages["Guild"]=page
        _,scroll,_=make_scrollable(page,bg=BG)
        ico=load_pil("guild.png",transparent=True)
        if ico:
            ico=ico.resize((120,120),Image.LANCZOS)
            ph=ImageTk.PhotoImage(ico); self._keep(ph)
            ctk.CTkLabel(scroll,image=ph,text="",fg_color=BG).pack(pady=(40,16))
        ctk.CTkLabel(scroll,text="Guild",font=("Georgia",28,"bold"),text_color=GOLD_LT).pack()
        ctk.CTkFrame(scroll,fg_color=GOLD_DK,height=1).pack(fill="x",padx=80,pady=12)
        ctk.CTkLabel(scroll,text="Coming Soon",font=("Palatino Linotype",18,"italic"),
                     text_color="#cc3333").pack(pady=8)

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
