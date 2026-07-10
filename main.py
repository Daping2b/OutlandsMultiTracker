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
}

BONUS_ICONS = {
    "sanctuary":  "bonus_sanctuary.png",
    "challenger": "bonus_challenger.png",
    "respawn":    "bonus_respawn.png",
    "gold_loot":  "bonus_gold_loot.png",
    "experience": "bonus_experience.png",
}

def _expand_abbrev(s: str) -> str:
    """Expand common Outlands dungeon name abbreviations for bonus matching."""
    return (s.lower()
             .replace("cath.", "cathedral")
             .replace("cath ",  "cathedral ")
             .replace("cath$",  "cathedral")
             .strip())


def _clean_item_name(name: str) -> str:
    """Remove parenthetical suffixes from item names, EXCEPT hue codes.
    'Iron Ingots (Valorite)' -> 'Iron Ingots'
    'Dagger (hue 1234)'      -> 'Dagger (hue 1234)'
    """
    import re as _re
    return _re.sub(r'\s*\([^)]*\)', lambda m: m.group(0) if 'hue' in m.group(0).lower() else '', name).strip()


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
            xp_m=re.search(r'\(([\w ]+?) Aspect ([\d,\.]+)/([\d,]+) xp\)',msg)
            if xp_m:
                asp=xp_m.group(1); xp_cur=float(xp_m.group(2).replace(",","")); xp_max=float(xp_m.group(3).replace(",",""))
                player=cur.get("player","") if cur else get_player(ts)
                xp_events.append({"ts":ts,"player":player,"aspect":asp,"xp_cur":xp_cur,"xp_max":xp_max})
                if cur is not None:
                    asp_first.setdefault(asp,(xp_cur,xp_max))
                    cur["aspects"][asp]=(xp_cur,xp_max,asp_first[asp])
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
            total_cat = sum(merged[cat].values())
            lines.append(f"  [{cat}] ({total_cat:,})")
            if cat == "Unidentified Items": continue
            for n,q in sorted(merged[cat].items()): lines.append(f"    {_clean_item_name(n)}: {q:,}")
    else:
        lines.append("")
        for cat in sorted(sessions[0].get("loots",{})):
            cat_items = sessions[0]["loots"][cat]
            lines.append(f"  [{cat}] ({sum(cat_items.values()):,})")
            if cat == "Unidentified Items": continue
            for n,q in sorted(cat_items.items()): lines.append(f"    {_clean_item_name(n)}: {q:,}")
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
    return get_from, get_to, do_all

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
            self._main_icon_path = ico_path
            # Re-apply after window is fully drawn
            self.after(500, lambda: self.iconbitmap(ico_path))
        except Exception:
            ico_pil = load_pil("O-MTSmall_128x128.png", (64,64), transparent=True)
            if ico_pil:
                ph = ImageTk.PhotoImage(ico_pil)
                self._keep(ph)
                self._main_icon_ph = ph  # persist reference
                self.iconphoto(True, ph)
                self.after(500, lambda: self.iconphoto(True, ph))

        # Reappliquer l icone OMT quand la fenetre recupere le focus
        # CTk remplace l icone par sa plume quand un CTkToplevel s ouvre
        def _reapply_main_icon(event=None):
            if not self.winfo_exists(): return
            # Ne rien faire si l icone n est pas encore initialisee
            if not hasattr(self, "_main_icon_path") and not hasattr(self, "_main_icon_ph"): return
            try:
                if hasattr(self, "_main_icon_path"):
                    self.iconbitmap(self._main_icon_path)
                elif hasattr(self, "_main_icon_ph"):
                    self.iconphoto(True, self._main_icon_ph)
            except Exception:
                pass
        self._reapply_main_icon = _reapply_main_icon
        self.bind("<FocusIn>", _reapply_main_icon)
        # <Map> retire - se declenche trop tot au demarrage avant init icone
        self.after(1500, _reapply_main_icon)

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
        self._build_home()
        self._build_log()
        # Lazy: other pages built on first visit
        self._built_pages = {"Home", "Log Analysis"}
        self._show("Home")
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
        elif name == "Guild" and hasattr(self, '_guild_page'):
            # Already built — re-render to pick up new token/state
            self._guild_render()
        for n,f in self._pages.items():
            f.pack_forget()
            btn=self._tb.get(n)
            if btn: btn.configure(text_color=DIM2,fg_color=BG4,border_color=BORDER)
        if name in self._pages:
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
    def _build_log(self):
        page=ctk.CTkFrame(self._body,fg_color=BG,corner_radius=0)
        self._pages["Log Analysis"]=page
        top=ctk.CTkFrame(page,fg_color=BG2,height=54,corner_radius=0); top.pack(fill="x"); top.pack_propagate(False)
        ctk.CTkFrame(top,fg_color=GOLD_DK,height=1,corner_radius=0).place(relx=0,rely=1.0,relwidth=1.0,anchor="sw")
        gold_btn(top,"⟳  LOAD LOGS",self._load_logs,w=155,h=36).pack(side="left",padx=10,pady=9)
        self._path_lbl(top).pack(side="left",padx=4)
        ctk.CTkButton(top,text="…",width=32,height=30,fg_color=BG4,border_color=BORDER,border_width=1,command=self._set_path).pack(side="left")
        # Upload All Guild Sessions checkbox
        self._upload_all_var = tk.BooleanVar(value=self.settings.get("guild_upload_all", False))
        ctk.CTkCheckBox(top, text="Upload All to Guild",
                         variable=self._upload_all_var,
                         font=F_SMALL, text_color=DIM,
                         checkmark_color=GOLD, fg_color=ACCENT2, border_color=BORDER,
                         command=self._on_upload_all_toggle).pack(side="right", padx=12)

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
        self._get_from, self._get_to, self._do_all_time = date_row(frow, self._refresh, self._all_time_log)
        dim_btn(frow,"🗑 Delete",self._delete_selected,w=95).pack(side="right",padx=2)
        dim_btn(frow,"📤 Upload Guild",self._upload_selected_to_guild,w=130).pack(side="right",padx=2)
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
                        if _expand_abbrev(k) in _expand_abbrev(base) or _expand_abbrev(base) in _expand_abbrev(k):
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

    def _row_tip_show(self, event, text):
        """Show tooltip for bonus icon in session rows."""
        try:
            if not hasattr(self, "_tv_tip") or not self._tv_tip:
                self._tv_tip = tk.Toplevel(self)
                self._tv_tip.wm_overrideredirect(True)
                self._tv_tip.attributes("-topmost", True)
                self._tv_tip_lbl = tk.Label(self._tv_tip, background="#1a1a1a",
                                            foreground=GOLD_LT, font=F_SMALL,
                                            relief="solid", borderwidth=1, padx=6, pady=3)
                self._tv_tip_lbl.pack()
            self._tv_tip_lbl.configure(text=text)
            self._tv_tip.wm_geometry(f"+{event.x_root+14}+{event.y_root+6}")
            self._tv_tip.deiconify()
        except Exception:
            pass

    def _row_tip_hide(self, event):
        if hasattr(self, "_tv_tip") and self._tv_tip:
            try: self._tv_tip.withdraw()
            except: pass

    def _on_act(self,_):
        sel=self._act_tv.selection()
        if not sel: return
        self._act_f=sel[0]
        # If no dates entered, stay in All Time
        has_dates = bool(self._get_from() or self._get_to())
        self._refresh(ignore_dates=not has_dates)


    def _filtered(self,ignore_dates=False):
        ss=list(self.sessions); f=self._act_f
        def _loc(s): return s.get("location") or ""
        def _typ(s): return s.get("type") or ""
        if   f=="Boating":      ss=[s for s in ss if "Boating"  in _typ(s)]
        elif f=="Harvesting":   ss=[s for s in ss if "Harvest"  in _typ(s)]
        elif f.startswith("dl_"): nm=f[3:];   ss=[s for s in ss if _loc(s)==nm]
        elif f.startswith("db_"): base=f[3:]; ss=[s for s in ss if re.sub(r'\s+Lv-\d+$','',_loc(s)).strip()==base]
        elif f=="Dungeon":      ss=[s for s in ss if "Creature Farming" in _typ(s) or _loc(s)]
        elif f=="wild_global":  ss=[s for s in ss if not _loc(s) and "Boating" not in _typ(s) and "Harvest" not in _typ(s)]
        elif f=="Wilderness":   ss=[s for s in ss if not _loc(s) and "Boating" not in _typ(s) and "Harvest" not in _typ(s)]
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
        for i,s in enumerate(ss):
            try: self._draw_row(i,s)
            except Exception as e: print(f"[ROW] draw error: {e}")

    def _set_char(self,n): self._char_f=n; self._refresh()
    def _sort_by(self, col):
        if self._sort_col==col: self._sort_rev=not self._sort_rev
        else: self._sort_col=col; self._sort_rev=False
        self._refresh()

    # Columns: (key, label, icon_file, width) — GAP=4 between each column in header AND rows
    COL_GAP = 4
    COLS=[
        ("",         "",           None,                               40),
        ("player",   "Player",     "woodenshield.png",                100),
        ("type",     "Type",       "tinkering_globe.png",             155),
        ("date",     "Date",       "carpentrycraftingmanual.png",     105),
        ("dur",      "Dur.",       "tinkering_clock.png",              68),
        ("golds",    "Golds",      "goldpile.png",                    105),
        ("doubloons","Doubloons",  "doubloons1.png",                  105),
        ("rare",     "Rare",       "arcanescroll1.png",                80),
        ("bonus",    "Bonus",      "bonus_experience.png",             90),
        ("harvest",  "Harvest",    "hatchetiron1.png",                 85),
        ("exp",      "Exp",        "chromaticcore1.png",              100),
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
        # Pack expand button FIRST (side=right) so it's always visible
        eb=ctk.CTkButton(row,text="\u25b6",width=30,height=30,fg_color="transparent",text_color=DIM2,hover_color=BG4,font=F_BODY)
        eb.pack(side="right",padx=6)
        detail=ctk.CTkFrame(outer,fg_color=BG,corner_radius=0); state=[False]
        spacer=ctk.CTkFrame(outer,fg_color=BG3,height=3,corner_radius=0)
        def toggle(df=detail,st=state,btn=eb,sess=s,sp=spacer):
            if st[0]:
                df.pack_forget(); sp.pack_forget()
                btn.configure(text="\u25b6"); st[0]=False
            else:
                df.pack(fill="x",pady=(1,0)); sp.pack(fill="x")
                btn.configure(text="\u25bc"); st[0]=True
                if not df.winfo_children(): self._populate_detail(df,sess)
        eb.configure(command=toggle)
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
        if sess_bonus and bonus_type in BONUS_ICONS:
            key = (bonus_type, "row")
            if key not in getattr(self, "_row_bonus_photos", {}):
                if not hasattr(self, "_row_bonus_photos"):
                    self._row_bonus_photos = {}
                ph = make_photo(BONUS_ICONS[bonus_type], (32,32), transparent=True)
                if ph:
                    self._row_bonus_photos[key] = ph
            bonus_photo = getattr(self, "_row_bonus_photos", {}).get(key)

        vals=[
            (s.get("player","?"), self.COLS[1][3], False),
            (stype,               self.COLS[2][3], True),
            (dt,                  self.COLS[3][3], False),
            (fmt_dur(mins),       self.COLS[4][3], False),
            (f"{gold:,}\n({rate(gold,mins)})",    self.COLS[5][3], False),
            (f"{doub:,}\n({rate(doub,mins)})",    self.COLS[6][3], False),
            (f"{rare}\n({rate(rare,mins)})",       self.COLS[7][3], False),
            (None,                                 self.COLS[8][3], False),  # bonus
            (f"{harv:,}\n({rate(harv,mins)})",    self.COLS[9][3], False),
            (f"{exp:,.0f}\n({rate(exp,mins)})",   self.COLS[10][3], False),
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
                    tip_text = f"{sess_bonus.get('label','')}  {sess_bonus.get('value','')}"
                    ico_lbl.bind("<Enter>", lambda e, t=tip_text: self._row_tip_show(e, t))
                    ico_lbl.bind("<Leave>", self._row_tip_hide)
                else:
                    ctk.CTkLabel(cell, text="—", width=cw, text_color=DIM2,
                                 font=F_BODY, justify="center").pack(expand=True)
            else:
                lbl = ctk.CTkLabel(row, text=text, width=cw, text_color=TEXT, font=F_BODY,
                                   justify="center", wraplength=cw-4 if wrap else 0)
                lbl.pack(side="left", padx=(gap,0), pady=2)

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
                    ctk.CTkLabel(rf,text=_clean_item_name(item),text_color=TEXT,font=F_SMALL,anchor="w").pack(side="left")
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
        try:
            ico = str(ASSETS_DIR / "O-MTSmall.ico")
            modal.after(250, lambda: modal.iconbitmap(ico) if modal.winfo_exists() else None)
        except Exception:
            pass
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
            known=set(Path(f).name if (os.sep in f or "/" in f) else f for f in raw_known)
            new_s,new_x=parse_logs(files,self.dung_data,self.wild_data,known,progress_cb)
            self.sessions.extend(new_s); self.xp_events.extend(new_x)
            self.sess_db["known_files"]=list(known)
            self.sess_db["sessions"]=self._ser_sess(self.sessions)
            save_json(SESSIONS_F,self.sess_db)
            self.xp_db["events"]=self._ser_xp(self.xp_events)
            save_json(XP_F,self.xp_db)
            total_s=len(self.sessions)
            # Auto-upload new sessions if Upload All is enabled
            if new_s and getattr(self, "_guild_session_token", None) and self.settings.get("guild_upload_all"):
                self.after(500, self._guild_upload_all)
            self.after(0,lambda ns=len(new_s),ts=total_s,tf=len(files):self._load_done(modal,ns,ts,tf))
        threading.Thread(target=do_load,daemon=True).start()

    def _load_done(self,modal,new_s,total_s,total_files):
        try:
            modal.grab_release()  # libérer le grab avant destroy
            modal.destroy()
        except Exception:
            pass
        self._refresh()
        def _show():
            self.lift(); self.focus_force()
            messagebox.showinfo("Done",f"{total_s} session(s) chargée(s)  (+{new_s} nouvelle(s))\n{total_files} fichier(s) log analysé(s).")
        self.after(150, _show)

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
        # ── Ligne 1 : Date range | View | Aspect Detail ──────────────────────
        bar1 = ctk.CTkFrame(page, fg_color=BG2, height=48, corner_radius=0)
        bar1.pack(fill="x"); bar1.pack_propagate(False)
        self._xget_from, self._xget_to, _ = date_row(bar1, self._refresh_xp, self._all_time_xp)
        ctk.CTkFrame(bar1, fg_color=BORDER, width=1, corner_radius=0).pack(side="left", fill="y", pady=8, padx=4)
        ctk.CTkLabel(bar1, text="  View:", text_color=DIM2, font=F_BODY).pack(side="left", padx=(8,4))
        self._xp_view = tk.StringVar(value="day")
        for label, val in [("Monthly","month"), ("Daily","day"), ("Hourly","hour")]:
            ctk.CTkRadioButton(bar1, text=label, variable=self._xp_view, value=val,
                               font=F_SMALL, text_color=TEXT, fg_color=GOLD, hover_color=GOLD_LT,
                               command=self._draw_xp).pack(side="left", padx=6)
        ctk.CTkFrame(bar1, fg_color=BORDER, width=1, corner_radius=0).pack(side="left", fill="y", pady=8, padx=8)
        self._xp_detail = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(bar1, text="Aspect Detail", variable=self._xp_detail,
                        font=F_SMALL, text_color=DIM2, fg_color=GOLD_DK,
                        checkmark_color=GOLD, hover_color=BG3,
                        command=self._draw_xp).pack(side="left", padx=8)
        ctk.CTkFrame(bar1, fg_color=GOLD_DK, height=1, corner_radius=0).place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

        # ── Ligne 2 : Character | Export / Discord ───────────────────────────
        bar2 = ctk.CTkFrame(page, fg_color=BG2, height=44, corner_radius=0)
        bar2.pack(fill="x"); bar2.pack_propagate(False)
        ctk.CTkLabel(bar2, text="  Character:", text_color=DIM2, font=F_BODY).pack(side="left", padx=(16,4))
        self._xp_cbar = ctk.CTkScrollableFrame(bar2, fg_color="transparent", height=36, orientation="horizontal")
        self._xp_cbar.pack(side="left", fill="x", expand=True, padx=(0,4))
        dim_btn(bar2, "Copy Discord", self._xp_discord, w=118).pack(side="right", padx=4, pady=4)
        dim_btn(bar2, "Export CSV",   self._xp_csv,     w=105).pack(side="right", padx=2, pady=4)
        ctk.CTkFrame(bar2, fg_color=GOLD_DK, height=1, corner_radius=0).place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")
        self._xp_chars = set()
        # Chart
        self._xp_chart=ctk.CTkFrame(page,fg_color=BG)
        self._xp_chart.pack(fill="both",expand=True,pady=(8,4))
        # Table
        self._xp_table=ctk.CTkScrollableFrame(page,fg_color=BG2,height=220,
                                               border_width=1,border_color=BORDER,
                                               width=800)
        self._xp_table.pack(anchor="center",pady=(0,8))
        self._all_time_xp()  # All Time + All Characters par defaut

    def _all_time_xp(self):
        players=sorted(set(e["player"] for e in self.xp_events if e.get("player")))
        self._xp_chars=set(players)
        self._refresh_xp(skip_draw=True)  # reconstruit les boutons sans redessiner
        self._draw_xp(ignore_dates=True)   # force all-time en un seul rendu

    def _refresh_xp(self, skip_draw=False):
        for w in self._xp_cbar.winfo_children(): w.destroy()
        players=sorted(set(e["player"] for e in self.xp_events if e.get("player")))
        # All button
        all_sel = (self._xp_chars == set(players)) if players else False
        ctk.CTkButton(self._xp_cbar,text="All",width=60,height=30,
                      fg_color=GOLD if all_sel else BG4,
                      text_color="#050505" if all_sel else DIM2,
                      hover_color=GOLD_LT,corner_radius=4,font=F_BODY,
                      border_width=1,border_color=BORDER,
                      command=self._tog_xp_all).pack(side="left",padx=(0,6))
        for p in players:
            sel=p in self._xp_chars
            ctk.CTkButton(self._xp_cbar,text=p,width=95,height=30,
                          fg_color=GOLD if sel else BG4,text_color="#050505" if sel else DIM2,
                          hover_color=GOLD_LT,corner_radius=4,font=F_BODY,
                          border_width=1,border_color=BORDER,
                          command=lambda n=p:self._tog_xp(n)).pack(side="left",padx=2)
        if not skip_draw: self._draw_xp()

    def _tog_xp_all(self):
        players=sorted(set(e["player"] for e in self.xp_events if e.get("player")))
        if self._xp_chars == set(players):
            self._xp_chars=set()
        else:
            self._xp_chars=set(players)
        self._refresh_xp()

    def _tog_xp(self,n):
        if n in self._xp_chars: self._xp_chars.discard(n)
        else: self._xp_chars.add(n)
        self._refresh_xp()
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

        show_detail = getattr(self, "_xp_detail", None) and self._xp_detail.get()

        if not show_detail:
            # Mode simple : une seule barre doree = XP total
            totals = np.array([sum(bucket_asp[m].values()) for m in buckets])
            bars = ax.bar(x, totals, color=GOLD_DK, width=0.78, edgecolor="none", label="XP")
            for bar, val in zip(bars, totals):
                bar_data.append((bar, "XP", val))
            # Labels au-dessus des barres
            ax.bar_label(bars,
                         labels=[f"{int(v):,}" if v > 0 else "" for v in totals],
                         padding=4,
                         color=GOLD_LT,
                         fontsize=8,
                         fontweight="bold")
        else:
            # Mode detail : barres empilees par aspect
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


    # Cumulative XP per aspect tier (from wiki)
    ASPECT_XP_CUMUL = []
    _c = 0
    for _t,_x in [(1,500),(2,1000),(3,1500),(4,2000),(5,2500),(6,3000),(7,3500),(8,4000),(9,4500),(10,5000),(11,15000),(12,25000),(13,40000),(14,120000),(15,250000)]:
        _c += _x
        ASPECT_XP_CUMUL.append((_t, _x, _c))


    def _draw_xp_table(self, ev, last_xp):
        ctk.CTkLabel(self._xp_table, text="✦  Estimated Days to Next Level",
                     text_color=GOLD, font=F_TITLE).pack(anchor="center", pady=(8,4))
        ctk.CTkFrame(self._xp_table, fg_color=GOLD_DK, height=1).pack(fill="x", padx=8, pady=(0,6))
        hdr=ctk.CTkFrame(self._xp_table, fg_color=BG3); hdr.pack(anchor="center", pady=(0,4))
        for col,w in [("Aspect",125),("Tier",50),("Current XP",115),("Max XP",115),
                      ("Remaining",115),("Avg XP/day",115),("Est. Days",100)]:
            ctk.CTkLabel(hdr, text=col, width=w, text_color=GOLD,
                         font=F_BODY_B, justify="center").pack(side="left", padx=4, pady=4)
        seen={}
        for key,(xp_cur,xp_max) in sorted(last_xp.items()):
            _,asp=key
            if asp in seen: continue
            seen[asp]=True
            asp_ev=sorted([e for e in ev if e["aspect"]==asp], key=lambda x:x["ts"])
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
            tier=0; cumul_prev=0
            for t,xt,xc in self.ASPECT_XP_CUMUL:
                if xp_cur<xc: tier=t; break
                cumul_prev=xc; tier=t
            color=ASPECT_COLORS.get(asp,TEXT)
            row=ctk.CTkFrame(self._xp_table, fg_color=BG2, corner_radius=4)
            row.pack(anchor="center", pady=1)
            for text,w in [(asp,125),(str(tier),50),(f"{xp_cur:,.1f}",115),(f"{xp_max:,.0f}",115),
                           (f"{remaining:,.1f}",115),(f"{avg_day:,.1f}",115),
                           (f"{est:.1f}d" if est else "—",100)]:
                ctk.CTkLabel(row, text=text, width=w,
                             text_color=color if text==asp else TEXT,
                             font=F_BODY_B if text==asp else F_BODY,
                             justify="center").pack(side="left", padx=4, pady=3)

    def _xp_csv(self):
        """Export XP data for selected characters to CSV."""
        import csv as _csv
        ev = [e for e in self.xp_events if e.get("player","") in self._xp_chars] if self._xp_chars else list(self.xp_events)
        if not ev:
            messagebox.showinfo("Export CSV","No XP data to export."); return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
               filetypes=[("CSV files","*.csv")],
               initialfile="xp_export.csv",
               title="Export XP as CSV")
        if not path: return
        # Build last_xp map
        last_xp = {}
        for e in sorted(ev, key=lambda x:x["ts"]):
            last_xp[(e["player"],e["aspect"])] = (e["xp_cur"], e["xp_max"])
        rows = []
        seen = {}
        for key,(xp_cur,xp_max) in sorted(last_xp.items()):
            player,asp = key
            if asp in seen.get(player,set()): continue
            seen.setdefault(player,set()).add(asp)
            asp_ev = sorted([e for e in ev if e["aspect"]==asp and e.get("player")==player], key=lambda x:x["ts"])
            total_g=0; prev={}
            for e in asp_ev:
                k2=(e["player"],e["aspect"])
                if k2 in prev:
                    pc,pm=prev[k2]
                    g=(e["xp_cur"]-pc) if e["xp_cur"]>=pc else (pm-pc)+e["xp_cur"]
                    total_g+=max(0,g)
                prev[k2]=(e["xp_cur"],e["xp_max"])
            span=max(1.0,(asp_ev[-1]["ts"]-asp_ev[0]["ts"]).total_seconds()/86400) if len(asp_ev)>=2 else 1.0
            avg=total_g/span; remaining=max(0,xp_max-xp_cur)
            est=remaining/avg if avg>0 else None
            tier=0; cumul_prev=0
            for t,xt,xc in self.ASPECT_XP_CUMUL:
                if xp_cur<xc: tier=t; break
                cumul_prev=xc; tier=t
            total_xp=cumul_prev+xp_cur
            rows.append({"Player":player,"Aspect":asp,"Tier":tier,
                         "Current XP":f"{xp_cur:.1f}","Max XP":f"{xp_max:.0f}",
                         "Total XP":f"{total_xp:.1f}","Remaining":f"{remaining:.1f}",
                         "Avg XP/day":f"{avg:.1f}","Est. Days":f"{est:.1f}" if est else "—"})
        try:
            with open(path,"w",newline="",encoding="utf-8") as f:
                w=_csv.DictWriter(f,fieldnames=["Player","Aspect","Tier","Current XP","Max XP","Total XP","Remaining","Avg XP/day","Est. Days"])
                w.writeheader(); w.writerows(rows)
            messagebox.showinfo("Done",f"Exported {len(rows)} aspect(s) to {path}")
        except Exception as e:
            messagebox.showerror("Error",str(e))

    def _xp_discord(self):
        """Copy XP summary for selected characters as Discord-formatted text."""
        ev = [e for e in self.xp_events if e.get("player","") in self._xp_chars] if self._xp_chars else list(self.xp_events)
        if not ev:
            messagebox.showinfo("Copy Discord","No XP data."); return
        last_xp = {}
        for e in sorted(ev, key=lambda x:x["ts"]):
            last_xp[(e["player"],e["aspect"])] = (e["xp_cur"], e["xp_max"])
        chars = sorted(self._xp_chars) if self._xp_chars else sorted(set(e["player"] for e in ev if e.get("player")))
        lines = ["```","═══ OUTLANDS MULTI TRACKER — XP ═══"]
        for player in chars:
            lines.append(f"\n[ {player} ]")
            seen = set()
            for key,(xp_cur,xp_max) in sorted(last_xp.items()):
                p,asp = key
                if p!=player or asp in seen: continue
                seen.add(asp)
                asp_ev = sorted([e for e in ev if e["aspect"]==asp and e.get("player")==player], key=lambda x:x["ts"])
                total_g=0; prev={}
                for e in asp_ev:
                    k2=(e["player"],e["aspect"])
                    if k2 in prev:
                        pc,pm=prev[k2]
                        g=(e["xp_cur"]-pc) if e["xp_cur"]>=pc else (pm-pc)+e["xp_cur"]
                        total_g+=max(0,g)
                    prev[k2]=(e["xp_cur"],e["xp_max"])
                span=max(1.0,(asp_ev[-1]["ts"]-asp_ev[0]["ts"]).total_seconds()/86400) if len(asp_ev)>=2 else 1.0
                avg=total_g/span; remaining=max(0,xp_max-xp_cur)
                est=remaining/avg if avg>0 else None
                pct=xp_cur/xp_max*100 if xp_max>0 else 0
                tier=0; cumul_prev=0
                for t,xt,xc in self.ASPECT_XP_CUMUL:
                    if xp_cur<xc: tier=t; break
                    cumul_prev=xc; tier=t
                total_xp=cumul_prev+xp_cur
                est_txt=f"{est:.1f}d" if est else "—"
                lines.append(f"  {asp:<12} T{tier}  {xp_cur:>9,.0f}/{xp_max:,.0f} ({pct:.0f}%)  total:{total_xp:,.0f}  avg:{avg:,.0f}/d  est:{est_txt}")
        lines.append("```")
        text="\n".join(lines)
        self.clipboard_clear(); self.clipboard_append(text)
        messagebox.showinfo("Copied!","XP data copied in Discord format.")

    # ═══════════════════════════════════════════════════════════════════════════
    # GUILD
    # ═══════════════════════════════════════════════════════════════════════════
    # ── Guild API helper ───────────────────────────────────────────────────────
    GUILD_API = "https://outlands-multi-tracker.com"
    _guild_cache:   dict = {}  # class-level cache — per instance via _build_guild
    _GUILD_CACHE_TTL: int  = 30   # seconds before guild data is re-fetched
    _members_cache: dict = {}  # class-level members cache

    def _guild_api(self, method: str, path: str, params: dict = None, body: dict = None) -> dict:
        """Make a request to the Guild API. Returns dict or raises.

        If params contains a "token" key, it is sent as an Authorization: Bearer
        header instead of a URL query parameter — query strings end up in server
        logs and Referer headers, which is not where a session token should live.
        """
        import urllib.request, urllib.parse, json as _json
        params = dict(params) if params else {}
        token = params.pop("token", None)
        url = self.GUILD_API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = _json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json", "User-Agent": "OMT/1.0"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                return _json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode()
            try: msg = _json.loads(msg).get("detail", msg)
            except: pass
            raise RuntimeError(msg)
        except Exception as e:
            raise RuntimeError(str(e))

    def _build_guild(self):
        if not hasattr(self, "_guild_cache"): self._guild_cache = {}
        if not hasattr(self, "_members_cache"): self._members_cache = {}
        if not hasattr(self, "_guild_active_id"): self._guild_active_id = None
        page = ctk.CTkFrame(self._body, fg_color=BG, corner_radius=0)
        self._pages["Guild"] = page
        self._guild_session_token = self._load_guild_token()
        self._guild_page = page
        self._guild_render()

    def _guild_cache_get(self, key: str):
        """Return cached value if within TTL, else None."""
        import time
        entry = self._guild_cache.get(key)
        if entry and (time.time() - entry[0]) < self._GUILD_CACHE_TTL:
            return entry[1]
        return None

    def _guild_cache_set(self, key: str, value):
        """Store value in cache with current timestamp."""
        import time
        self._guild_cache[key] = (time.time(), value)

    def _load_guild_token(self) -> str | None:
        """Load persisted session token from settings."""
        return self.settings.get("guild_token")

    def _save_guild_token(self, token: str | None):
        """Persist session token in settings."""
        if token:
            self.settings["guild_token"] = token
        else:
            self.settings.pop("guild_token", None)
        save_json(SETTINGS_F, self.settings)

    def _guild_render(self):
        """Render Guild state — async token check to avoid blocking main thread."""
        for w in self._guild_page.winfo_children(): w.destroy()
        if not self._guild_session_token:
            self._guild_state_login()
            return
        # Show loading indicator while verifying token
        loading = ctk.CTkLabel(self._guild_page, text="Loading...",
                               text_color=DIM2, font=F_BODY)
        loading.pack(expand=True)
        def _check():
            try:
                me = self._guild_api("GET", "/auth/me",
                                     params={"token": self._guild_session_token})
                self.after(0, lambda: _render(me))
            except RuntimeError:
                self._guild_session_token = None
                self._save_guild_token(None)
                self.after(0, _on_token_invalid)
        def _on_token_invalid():
            for w in self._guild_page.winfo_children(): w.destroy()
            self._guild_state_login()
        def _render(me):
            for w in self._guild_page.winfo_children(): w.destroy()
            self._guild_me = me
            if me.get("memberships"):
                self._guild_state_guild(me)
            else:
                self._guild_state_profile(me)
        threading.Thread(target=_check, daemon=True).start()

    # ── State 1: Login ────────────────────────────────────────────────────────
    def _guild_state_login(self):
        p = self._guild_page
        ctk.CTkFrame(p, height=60, fg_color="transparent").pack()
        ico = load_pil("guild.png", transparent=True)
        if ico:
            ico = ico.resize((100, 100), Image.LANCZOS)
            ph  = ImageTk.PhotoImage(ico); self._keep(ph)
            ctk.CTkLabel(p, image=ph, text="", fg_color=BG).pack(pady=(20, 8))
        ctk.CTkLabel(p, text="Guild", font=("Georgia", 28, "bold"),
                     text_color=GOLD_LT).pack()
        ctk.CTkFrame(p, fg_color=GOLD_DK, height=1).pack(fill="x", padx=120, pady=12)
        ctk.CTkLabel(p, text="Connect your Discord account to access Guild features.",
                     font=F_BODY, text_color=DIM).pack(pady=(0, 20))
        ctk.CTkButton(p, text="🎮  Connect with Discord",
                      font=("Segoe UI", 14, "bold"),
                      fg_color="#5865F2", hover_color="#4752C4",
                      text_color="white", width=260, height=48,
                      corner_radius=8,
                      command=self._guild_do_login).pack()
        self._guild_status_lbl = ctk.CTkLabel(p, text="", text_color=DIM2, font=F_SMALL)
        self._guild_status_lbl.pack(pady=8)

    # ── State 2: Profile (logged in, no guild) ────────────────────────────────
    def _guild_state_profile(self, me: dict):
        p = self._guild_page
        hdr = ctk.CTkFrame(p, fg_color=BG2, height=70, corner_radius=0)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkFrame(hdr, fg_color=GOLD_DK, height=1).place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")
        self._guild_load_avatar(hdr, me.get("avatar"), size=46)
        ctk.CTkLabel(hdr, text=me.get("username","?"),
                     font=("Segoe UI",15,"bold"), text_color=TEXT).pack(side="left", padx=8)
        gold_btn(hdr, "Logout", self._guild_logout, w=90, h=32).pack(side="right", padx=12)
        # Afficher le bouton SuperAdmin dans la nav principale si applicable
        if me.get("is_superadmin") and hasattr(self, "_sa_btn"):
            self._sa_btn.pack(side="right", padx=2, pady=8)
        ctk.CTkFrame(p, height=40, fg_color="transparent").pack()
        ctk.CTkLabel(p, text="You are not in any guild yet.",
                     font=F_HEAD, text_color=DIM).pack(pady=(0,4))
        ctk.CTkLabel(p, text="Create a new guild or join an existing one.",
                     font=F_BODY, text_color=DIM2).pack(pady=(0,30))
        btn_row = ctk.CTkFrame(p, fg_color="transparent"); btn_row.pack()
        gold_btn(btn_row, "⚔  Create Guild", self._guild_create_flow, w=180, h=44).pack(side="left", padx=12)
        dim_btn(btn_row,  "🔎  Join Guild",  self._guild_join_flow,   w=160, h=44).pack(side="left", padx=12)

    # ── State 3: Guild view — left nav + right content ────────────────────────
    def _guild_state_guild(self, me: dict):
        p = self._guild_page
        # Header
        hdr = ctk.CTkFrame(p, fg_color=BG2, height=70, corner_radius=0)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkFrame(hdr, fg_color=GOLD_DK, height=1).place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")
        self._guild_load_avatar(hdr, me.get("avatar"), size=46)
        ctk.CTkLabel(hdr, text=me.get("username","?"),
                     font=("Segoe UI",15,"bold"), text_color=TEXT).pack(side="left", padx=8)
        gold_btn(hdr, "Logout", self._guild_logout, w=90, h=32).pack(side="right", padx=12)
        # Afficher le bouton SuperAdmin dans la nav principale si applicable
        if me.get("is_superadmin") and hasattr(self, "_sa_btn"):
            self._sa_btn.pack(side="right", padx=2, pady=8)

        body = ctk.CTkFrame(p, fg_color=BG); body.pack(fill="both", expand=True)
        nav  = ctk.CTkFrame(body, fg_color=BG2, width=190, corner_radius=0)
        nav.pack(side="left", fill="y"); nav.pack_propagate(False)
        ctk.CTkFrame(nav, fg_color=GOLD_DK, width=1, corner_radius=0).pack(side="right", fill="y")
        self._guild_content = ctk.CTkFrame(body, fg_color=BG, corner_radius=0)
        self._guild_content.pack(side="left", fill="both", expand=True)
        self._guild_nav_btns = {}  # track nav buttons for active state

        memberships = me.get("memberships", [])
        self._guild_me = me

        def _nav_btn(parent, text, cmd, key):
            """Nav button that disables itself when active."""
            btn = ctk.CTkButton(parent, text=text, anchor="w",
                                fg_color="transparent", text_color=TEXT,
                                hover_color=BG3, font=F_SMALL, height=34,
                                command=lambda: _activate(key, cmd))
            btn.pack(fill="x", padx=4, pady=1)
            self._guild_nav_btns[key] = btn
            return btn

        def _activate(key, cmd):
            # Restore all buttons
            for k, b in self._guild_nav_btns.items():
                b.configure(fg_color="transparent", text_color=TEXT, state="normal")
            # Mark active
            if key in self._guild_nav_btns:
                self._guild_nav_btns[key].configure(fg_color=BG3, text_color=GOLD_LT, state="disabled")
            cmd()

        # ── Dropdown sélection de guilde ─────────────────────────────────────
        # Construit un dict {nom_affiché: membership_dict}
        guild_map = {}
        for m in memberships:
            gname = m.get("guild_name", m["guild_id"][:16])
            guild_map[gname] = m

        guild_names = list(guild_map.keys())

        def _render_guild_nav(gname):
            """Reconstruit les boutons de nav pour la guilde sélectionnée."""
            # Nettoyer les anciens boutons de guilde (pas la section Personal)
            for w in nav_guild_zone.winfo_children():
                w.destroy()
            # Retirer les keys de guilde de nav_btns
            guild_keys = [k for k in self._guild_nav_btns if k not in ("profile", "characters")]
            for k in guild_keys:
                self._guild_nav_btns.pop(k, None)

            m = guild_map[gname]
            guild_id  = m["guild_id"]
            omt_grade = m["omt_grade"]
            self._guild_active_id = guild_id  # stocker la guilde active

            ctk.CTkFrame(nav_guild_zone, fg_color=BORDER, height=1).pack(fill="x", padx=8, pady=(4,4))

            if omt_grade == "leader":
                _nav_btn(nav_guild_zone, "  \U0001f451  Guild Admin",
                         lambda gid=guild_id: self._guild_show_admin(gid),
                         f"admin_{guild_id}")
                _nav_btn(nav_guild_zone, "  \U0001f916  Bot",
                         lambda gid=guild_id: self._guild_show_bot(gid),
                         f"bot_{guild_id}")
            _nav_btn(nav_guild_zone, "  \U0001f465  Members",
                     lambda gid=guild_id: self._guild_show_members(gid),
                     f"members_{guild_id}")
            _nav_btn(nav_guild_zone, "  \U0001f4cb  Sessions",
                     lambda gid=guild_id: self._guild_show_sessions(gid),
                     f"sessions_{guild_id}")

            # Activer la section par défaut
            if omt_grade == "leader":
                _activate(f"admin_{guild_id}", lambda gid=guild_id: self._guild_show_admin(gid))
            else:
                _activate(f"members_{guild_id}", lambda gid=guild_id: self._guild_show_members(gid))

        if len(guild_names) > 1:
            # Dropdown guild — style distinctif en haut du nav
            ctk.CTkFrame(nav, fg_color=GOLD_DK, height=1).pack(fill="x", padx=0, pady=(0,0))
            guild_var = ctk.StringVar(value=guild_names[0])
            ctk.CTkOptionMenu(
                nav, variable=guild_var,
                values=guild_names,
                fg_color=BG4, button_color=GOLD_DK,
                button_hover_color=GOLD, text_color=GOLD_LT,
                dropdown_fg_color=BG2, dropdown_text_color=TEXT,
                dropdown_hover_color=BG3,
                font=F_BODY_B, width=190,
                dynamic_resizing=False,
                command=_render_guild_nav
            ).pack(padx=0, pady=0, fill="x")
            ctk.CTkFrame(nav, fg_color=GOLD_DK, height=1).pack(fill="x", padx=0, pady=(0,4))
        elif guild_names:
            # Une seule guilde — label distinctif pleine largeur
            ctk.CTkFrame(nav, fg_color=GOLD_DK, height=1).pack(fill="x", padx=0)
            ctk.CTkLabel(nav, text=f"  ⚔  {guild_names[0][:18]}",
                         text_color=GOLD_LT, font=F_BODY_B, anchor="w",
                         fg_color=BG4).pack(fill="x", padx=0, pady=0, ipady=8)
            ctk.CTkFrame(nav, fg_color=GOLD_DK, height=1).pack(fill="x", padx=0, pady=(0,4))

        # Zone nav dynamique — sous le dropdown
        nav_guild_zone = ctk.CTkFrame(nav, fg_color="transparent")
        nav_guild_zone.pack(fill="x")

        # Render initial avec la première guilde
        if guild_names:
            self._guild_active_id = guild_map[guild_names[0]]["guild_id"]
            _render_guild_nav(guild_names[0])

        # Personal section — toujours visible en bas
        ctk.CTkFrame(nav, fg_color=BORDER, height=1).pack(fill="x", padx=8, pady=(12,2))
        ctk.CTkLabel(nav, text="  Personal", text_color=DIM2,
                     font=F_SMALL, anchor="w").pack(fill="x", padx=8, pady=(2,0))
        _nav_btn(nav, "  \U0001f464  My Profile",  self._guild_show_profile,    "profile")
        _nav_btn(nav, "  \U0001f3ae  My Characters", self._guild_show_characters, "characters")

        # SuperAdmin accès via bouton ⚡ dans la nav principale

    # ── Nav loading helper ────────────────────────────────────────────────────
    def _guild_content_loading(self, title: str):
        """Clear content and show loading spinner."""
        for w in self._guild_content.winfo_children(): w.destroy()
        ctk.CTkLabel(self._guild_content, text=title,
                     font=F_HEAD, text_color=GOLD_LT, anchor="w").pack(fill="x", padx=16, pady=(12,4))
        ctk.CTkFrame(self._guild_content, fg_color=GOLD_DK, height=1).pack(fill="x", padx=16, pady=(0,8))
        lbl = ctk.CTkLabel(self._guild_content, text="\u23f3  Loading...",
                           text_color=DIM2, font=F_BODY)
        lbl.pack(expand=True)
        return lbl

    def _guild_content_header(self, title: str, pad_bottom: int = 8):
        """Clear guild content zone and render standard title + gold separator.
        Call at the start of every _guild_show_* render function.
        """
        for w in self._guild_content.winfo_children(): w.destroy()
        ctk.CTkLabel(self._guild_content, text=title,
                     font=F_HEAD, text_color=GOLD_LT, anchor="w").pack(fill="x", padx=16, pady=(12,4))
        ctk.CTkFrame(self._guild_content, fg_color=GOLD_DK, height=1).pack(fill="x", padx=16, pady=(0, pad_bottom))
        return self._guild_content

    # ── Members page ──────────────────────────────────────────────────────────
    def _guild_show_members(self, guild_id: str):
        STATUS_COLORS = {"online":"#23a55a","idle":"#f0b232","dnd":"#f23f43","offline":"#80848e"}
        # Show cached data immediately if available
        if guild_id in getattr(self, "_members_cache", {}):
            self._guild_content_loading("  \U0001f465  Members")
            self.after(10, lambda: _render(self._members_cache[guild_id]))
        else:
            self._guild_content_loading("  \U0001f465  Members")

        def _load():
            try:
                data = self._guild_api("GET", f"/guild/{guild_id}/members-full",
                                       params={"token": self._guild_session_token})
                if not hasattr(self, "_members_cache"): self._members_cache = {}
                self._members_cache[guild_id] = data
                self.after(0, lambda: _render(data))
            except RuntimeError as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: ctk.CTkLabel(
                    self._guild_content, text=f"Error: {msg}",
                    text_color=RED, font=F_BODY).pack(padx=16, pady=8))

        def _render(data):
            self._guild_content_header("  \U0001f465  Members")

            grade_names = data.get("grade_names", {
                "leader":"Guild Leader","officer":"Officer",
                "member":"Member","recruit":"Recruit"
            })
            members_by_grade = data.get("members_by_grade", {})
            grade_order = data.get("grade_order", ["leader","officer","member","recruit"])

            scroll = ctk.CTkScrollableFrame(self._guild_content, fg_color="transparent")
            scroll.pack(fill="both", expand=True, padx=8)

            for grade in grade_order:
                members = members_by_grade.get(grade, [])
                if not members: continue
                # Grade header
                ctk.CTkLabel(scroll, text=f"  {grade_names.get(grade, grade)} ({len(members)})",
                             font=F_BODY_B, text_color=GOLD, anchor="w").pack(fill="x", padx=8, pady=(10,2))
                ctk.CTkFrame(scroll, fg_color=BORDER, height=1).pack(fill="x", padx=8, pady=(0,4))
                # Rendu par batch de 20 pour ne pas bloquer l'UI
                BATCH_M = 20
                state_m = {"idx": 0}
                def _render_member_batch(members=members):
                    if not scroll.winfo_exists(): return  # navigation pendant le rendu
                    batch_end = min(state_m["idx"] + BATCH_M, len(members))
                    for mbr in members[state_m["idx"]:batch_end]:
                        mbr_wrap = ctk.CTkFrame(scroll, fg_color="transparent")
                        mbr_wrap.pack(fill="x", padx=4, pady=1)
                        row = ctk.CTkFrame(mbr_wrap, fg_color=BG2, corner_radius=4)
                        row.pack(fill="x")
                        # Status dot
                        status = mbr.get("discord_status","offline")
                        dot_color = STATUS_COLORS.get(status, STATUS_COLORS["offline"])
                        dot = ctk.CTkFrame(row, width=10, height=10, corner_radius=5,
                                           fg_color=dot_color)
                        dot.pack(side="left", padx=(10,4))
                        dot.pack_propagate(False)
                        # Name color: gold if connected to OMT, grey if not
                        name_color = GOLD if mbr.get("omt_connected") else DIM
                        ctk.CTkLabel(row, text=mbr.get("username","?"),
                                     font=F_BODY, text_color=name_color,
                                     anchor="w").pack(side="left", padx=4, pady=6)
                        # Zone dépliable pour les personnages (cachée par défaut)
                        chars_wrap = ctk.CTkFrame(mbr_wrap, fg_color=BG2, corner_radius=0)
                        # NE PAS packer chars_wrap ici — il sera packé au premier clic
                        # Buttons
                        dim_btn(row, "Présentiel",
                                lambda uid=mbr["user_id"]: self._guild_member_presentiel(uid),
                                w=90, h=26).pack(side="right", padx=4, pady=4)
                        def _make_char_btn(uid=mbr["user_id"], gid=guild_id, cw=chars_wrap):
                            b = dim_btn(row, "Characters", lambda: None, w=90, h=26)
                            b.configure(command=lambda u=uid, g=gid, c=cw, btn=b:
                                        self._guild_member_characters(u, row_frame=row, chars_wrap=c, btn=btn, guild_id=g))
                            b.pack(side="right", padx=4, pady=4)
                        _make_char_btn()
                    state_m["idx"] = batch_end
                    if state_m["idx"] < len(members):
                        scroll.after(0, _render_member_batch)
                _render_member_batch()

        threading.Thread(target=_load, daemon=True).start()

    def _guild_member_characters(self, user_id: str, row_frame=None, chars_wrap=None, btn=None, guild_id: str = None):
        """Déplie/replie les personnages d'un membre inline dans la liste."""
        if chars_wrap is None: return  # appelé sans contexte — ignorer

        # Toggle — pack/unpack le frame
        if chars_wrap.winfo_manager():
            # Déjà visible → masquer
            chars_wrap.pack_forget()
            if btn: btn.configure(text="Characters")
            return

        # Afficher le frame
        chars_wrap.pack(fill="x")
        if btn: btn.configure(text="Characters ▲")

        # Si déjà chargé, juste réafficher
        if chars_wrap.winfo_children():
            return

        ROLE_COLORS = {
            "pvp": "#5B9BD5", "pvm": "#FFD700", "pk": "#E05050",
            "harvester": "#7EC88A", "crafter": "#B57FD8",
        }
        ROLE_LABELS = {
            "pvp": "PvP", "pvm": "PvM", "pk": "PK",
            "harvester": "Harv.", "crafter": "Craft.",
        }
        ACCOUNT_LABELS = {1: "Main", 2: "Secondaire", 3: "Third", None: "Unknown"}

        loading = ctk.CTkLabel(chars_wrap, text="Loading...",
                               font=F_SMALL, text_color=DIM2)
        loading.pack(anchor="w", padx=20, pady=2)

        def _load():
            if not guild_id: return
            try:
                data = self._guild_api("GET", f"/guild/{guild_id}/characters/{user_id}",
                                       params={"token": self._guild_session_token})
                chars = data.get("characters", [])
                self.after(0, lambda: _render(chars))
            except RuntimeError as e:
                err = str(e)
                self.after(0, lambda m=err: loading.configure(
                    text=f"Error: {m}", text_color=RED) if chars_wrap.winfo_exists() else None)

        def _render(chars):
            if not chars_wrap.winfo_exists(): return
            loading.destroy()
            if not chars:
                ctk.CTkLabel(chars_wrap, text="No characters.",
                             font=F_SMALL, text_color=DIM2).pack(anchor="w", padx=20, pady=2)
                return
            # Grouper par compte
            accounts = {}
            for c in chars:
                acc = c.get("account_number")
                if acc not in (1, 2, 3): acc = None
                accounts.setdefault(acc, []).append(c)
            for acc_num in [k for k in (1, 2, 3, None) if k in accounts]:
                acc_label = ACCOUNT_LABELS.get(acc_num, f"Account {acc_num}")
                ctk.CTkLabel(chars_wrap, text=f"    {acc_label}",
                             font=F_SMALL_B, text_color=GOLD, anchor="w").pack(fill="x", padx=16, pady=(4,0))
                for c in accounts[acc_num]:
                    c_row = ctk.CTkFrame(chars_wrap, fg_color=BG3, corner_radius=3)
                    c_row.pack(fill="x", padx=20, pady=1)
                    ctk.CTkLabel(c_row, text=c["name"], font=F_SMALL,
                                 text_color=TEXT, anchor="w").pack(side="left", padx=8, pady=3)
                    tag_f = ctk.CTkFrame(c_row, fg_color="transparent")
                    tag_f.pack(side="left", padx=2)
                    for role in c.get("roles", []):
                        ctk.CTkLabel(tag_f, text=ROLE_LABELS.get(role, role),
                                     font=F_SMALL, text_color=BG,
                                     fg_color=ROLE_COLORS.get(role, DIM),
                                     corner_radius=3, width=36, height=16
                                     ).pack(side="left", padx=1)

        threading.Thread(target=_load, daemon=True).start()

    def _guild_member_presentiel(self, user_id: str):
        messagebox.showinfo("Présentiel", f"Présentiel for {user_id} — coming soon.")

    # ── Bot page ──────────────────────────────────────────────────────────────
    def _guild_show_bot(self, guild_id: str):
        self._guild_content_loading("  \U0001f916  Bot")

        def _load():
            try:
                g = self._guild_cache_get(guild_id)
                if g is None:
                    g = self._guild_api("GET", f"/guild/{guild_id}/full",
                                        params={"token": self._guild_session_token})
                    self._guild_cache_set(guild_id, g)
                self.after(0, lambda: _render(g))
            except RuntimeError as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: ctk.CTkLabel(
                    self._guild_content, text=f"Error: {msg}",
                    text_color=RED, font=F_BODY).pack(padx=16, pady=8))

        def _render(roles_data):
            self._guild_content_header("  \U0001f916  Bot", pad_bottom=16)
            bot_present = roles_data.get("bot_present", False)
            # ── Statut ────────────────────────────────────────────────────────
            status_row = ctk.CTkFrame(self._guild_content, fg_color="transparent")
            status_row.pack(pady=(0, 4))
            dot = ctk.CTkFrame(status_row, width=14, height=14, corner_radius=7,
                               fg_color="#23a55a" if bot_present else "#80848e")
            dot.pack_propagate(False)
            dot.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(status_row,
                         text="Bot is in the server" if bot_present else "Bot not detected",
                         font=F_BODY_B,
                         text_color="#23a55a" if bot_present else DIM2).pack(side="left")
            ctk.CTkFrame(self._guild_content, fg_color=BORDER, height=1).pack(fill="x", padx=40, pady=(8, 16))
            # ── Invite ────────────────────────────────────────────────────────
            def _invite():
                import webbrowser, threading
                def _do():
                    try:
                        d = self._guild_api("GET", "/guild/bot-invite-url",
                                            params={"server_id": guild_id})
                        self.after(0, lambda u=d["url"]: webbrowser.open(u))
                    except Exception as e:
                        err = str(e)
                        self.after(0, lambda m=err: messagebox.showerror("Error", m))
                threading.Thread(target=_do, daemon=True).start()
            gold_btn(self._guild_content, "\U0001f517  Invite Bot", _invite, w=200, h=42).pack(pady=4)
            ctk.CTkLabel(self._guild_content,
                         text="After inviting, click Bot again to refresh status.",
                         font=F_SMALL, text_color=DIM2).pack(pady=(0, 8))
            # ── Kick ──────────────────────────────────────────────────────────
            def _kick():
                if not messagebox.askyesno("Kick Bot",
                        "Remove the bot from this server?\nYou can re-invite it at any time."):
                    return
                def _do():
                    try:
                        self._guild_api("DELETE", f"/guild/{guild_id}",
                                        params={"token": self._guild_session_token})
                        self.after(0, lambda: [
                            messagebox.showinfo("Done", "Bot removed from server."),
                            self._guild_render()
                        ])
                    except RuntimeError as e:
                        err = str(e)
                        self.after(0, lambda msg=err: messagebox.showerror("Error", msg))
                threading.Thread(target=_do, daemon=True).start()
            if bot_present:
                ctk.CTkButton(self._guild_content, text="\U0001f6aa  Kick Bot",
                              width=200, height=42, fg_color="transparent",
                              hover_color="#5a1a1a", text_color=RED,
                              font=F_BODY, corner_radius=6,
                              command=_kick).pack(pady=4)
            # ── Placeholder future options ────────────────────────────────────
            ctk.CTkFrame(self._guild_content, fg_color=BORDER, height=1).pack(fill="x", padx=40, pady=(16, 8))
            ctk.CTkLabel(self._guild_content, text="More bot options coming soon.",
                         font=F_SMALL, text_color=DIM2).pack(pady=4)

        threading.Thread(target=_load, daemon=True).start()

    # ── Guild Admin page ──────────────────────────────────────────────────────
    def _guild_show_admin(self, guild_id: str):
        self._guild_content_loading("  \U0001f451  Guild Admin")
        all_roles      = []
        mappings_state = {}
        grades_state   = []
        perms_state    = set()   # {(grade, permission_key)}

        def _load():
            try:
                g = self._guild_cache_get(guild_id)
                if g is None:
                    g = self._guild_api("GET", f"/guild/{guild_id}/full",
                                        params={"token": self._guild_session_token})
                    self._guild_cache_set(guild_id, g)
                if g.get("bot_present"):
                    all_roles.extend(g.get("discord_roles", []))
                grade_names = g.get("grade_names", {"leader":"Guild Leader","officer":"Officer","member":"Member","recruit":"Recruit"})
                grade_order = g.get("grade_order", ["leader","officer","member","recruit"])
                for gk in grade_order:
                    grades_state.append({"key": gk, "name": grade_names.get(gk, gk.capitalize())})
                    mappings_state[gk] = []
                for rm in g.get("role_mappings", []):
                    gk = rm["omt_grade"]
                    if gk not in mappings_state: mappings_state[gk] = []
                    mappings_state[gk].append({"id": rm["discord_role_id"], "name": rm["discord_role_name"]})
                # Charger les permissions existantes dans perms_state
                for gp in g.get("grade_permissions", []):
                    key = (gp["grade"], gp["permission_key"])
                    perms_state.add(key)
                self.after(0, lambda gd=g: _render(gd))
            except RuntimeError as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: ctk.CTkLabel(
                    self._guild_content, text=f"Error: {msg}",
                    text_color=RED, font=F_BODY).pack(padx=16, pady=8))

        def _render(g):
            self._guild_content_header("  \U0001f451  Guild Admin")

            # ── Scrollable area for all accordions ───────────────────────────
            scroll = ctk.CTkScrollableFrame(self._guild_content, fg_color="transparent")
            scroll.pack(fill="both", expand=True, padx=16, pady=(0,0))

            accordion_frames = {}

            # ══ GRADE SYSTEM accordion ════════════════════════════════════════
            gs_state = {"open": False}
            gs_wrap  = ctk.CTkFrame(scroll, fg_color="transparent")
            gs_wrap.pack(fill="x", pady=(0,4))

            def _render_grade_system():
                for w in gs_wrap.winfo_children(): w.destroy()
                arrow = "\u25bc" if gs_state["open"] else "\u25b6"
                gs_hdr = ctk.CTkFrame(gs_wrap, fg_color=BG3, corner_radius=6)
                gs_hdr.pack(fill="x")
                ctk.CTkLabel(gs_hdr, text=f"  {arrow}  Grade System",
                             font=F_BODY_B, text_color=GOLD_LT, anchor="w").pack(side="left", padx=10, pady=8)
                def _toggle_gs():
                    gs_state["open"] = not gs_state["open"]
                    _render_grade_system()
                gs_hdr.bind("<Button-1>", lambda e: _toggle_gs())
                if not gs_state["open"]: return
                # Plain frame — no scroll, grades display fully
                gf_inner = ctk.CTkFrame(gs_wrap, fg_color="transparent")
                gf_inner.pack(fill="x", padx=4, pady=(2,4))
                for ge in grades_state:
                    gk = ge["key"]
                    gf = ctk.CTkFrame(gf_inner, fg_color="transparent")
                    gf.pack(fill="x", pady=2)
                    accordion_frames[gk] = gf
                    accordion_frames[gk]._open = True
                    _render_accordion(ge)
                def _add_grade():
                    import secrets as _sec
                    nk = "grade_" + _sec.token_hex(4)
                    grades_state.append({"key": nk, "name": f"Grade {len(grades_state)+1}"})
                    mappings_state[nk] = []
                    _render_grade_system()
                dim_btn(gf_inner, "+ Add Grade", _add_grade, w=130, h=30).pack(anchor="w", padx=4, pady=4)

            def _render_accordion(ge):
                gk    = ge["key"]
                gname = ge["name"]
                outer = accordion_frames.get(gk)
                if not outer: return
                for w in outer.winfo_children(): w.destroy()
                # Default closed
                is_open = getattr(outer, "_open", False)
                arrow   = "\u25bc" if is_open else "\u25b6"
                hdr_row = ctk.CTkFrame(outer, fg_color=BG3, corner_radius=4)
                hdr_row.pack(fill="x")
                ctk.CTkLabel(hdr_row, text=f"  {arrow}  {gname}",
                             font=F_BODY_B, text_color=GOLD, anchor="w").pack(side="left", padx=8, pady=6)
                name_var = tk.StringVar(value=gname)
                ctk.CTkEntry(hdr_row, textvariable=name_var, width=140, height=26,
                             font=F_SMALL, fg_color=BG4, border_color=BORDER,
                             text_color=TEXT).pack(side="left", padx=4)
                def _save_name(gk2=gk, var=name_var, ge2=ge):
                    ge2["name"] = var.get()
                ctk.CTkButton(hdr_row, text="\u2713", width=26, height=26,
                              fg_color=BG4, hover_color=GOLD_DK, text_color=GOLD,
                              font=F_SMALL, corner_radius=4, command=_save_name).pack(side="left", padx=2)
                if gk != "leader":
                    def _del_grade(gk2=gk, ge2=ge):
                        grades_state.remove(ge2)
                        mappings_state.pop(gk2, None)
                        if gk2 in accordion_frames: accordion_frames[gk2].destroy()
                        _render_grade_system()
                    ctk.CTkButton(hdr_row, text="\u00d7", width=26, height=26,
                                  fg_color="transparent", hover_color=RED, text_color=RED,
                                  font=F_BODY_B, corner_radius=4,
                                  command=_del_grade).pack(side="right", padx=4)
                def _toggle(o=outer, ge2=ge):
                    o._open = not getattr(o, "_open", False)
                    _render_accordion(ge2)
                hdr_row.bind("<Button-1>", lambda e, o=outer, ge2=ge: _toggle(o, ge2))
                if not is_open: return
                # Body only shown when open
                body_f = ctk.CTkFrame(outer, fg_color=BG2, corner_radius=0)
                body_f.pack(fill="x", padx=2, pady=(0,2))
                roles = mappings_state.get(gk, [])
                if roles:
                    roles_row = ctk.CTkFrame(body_f, fg_color="transparent")
                    roles_row.pack(fill="x", padx=8, pady=(6,2))
                    for role in roles:
                        tag = ctk.CTkFrame(roles_row, fg_color=BG4, corner_radius=4)
                        tag.pack(side="left", padx=2)
                        ctk.CTkLabel(tag, text=role["name"], font=F_SMALL,
                                     text_color=TEXT).pack(side="left", padx=(6,2))
                        ctk.CTkButton(tag, text="\u00d7", width=18, height=18,
                                      fg_color="transparent", text_color=DIM2, hover_color=RED,
                                      font=F_SMALL,
                                      command=lambda r=role, gk2=gk, ge2=ge: [
                                          mappings_state[gk2].remove(r), _render_accordion(ge2)
                                      ]).pack(side="left", padx=(0,2))
                def _add_role(gk2=gk, ge2=ge):
                    if not all_roles:
                        messagebox.showinfo("Info", "Invite the bot first to load roles.")
                        return
                    popup = ctk.CTkToplevel(self); popup.title("Add Role")
                    popup.geometry("280x340"); popup.configure(fg_color=BG); popup.grab_set()
                    self._set_win_icon(popup)
                    sf = ctk.CTkScrollableFrame(popup, fg_color=BG2, height=280)
                    sf.pack(fill="both", expand=True, padx=8, pady=8)
                    used = {r["id"] for roles in mappings_state.values() for r in roles}
                    for role in all_roles:
                        if role["id"] in used: continue
                        def _pick(r=role, gk3=gk2, ge3=ge2):
                            if gk3 not in mappings_state: mappings_state[gk3] = []
                            mappings_state[gk3].append(r)
                            _render_accordion(ge3); popup.destroy()
                        ctk.CTkButton(sf, text=role["name"], anchor="w",
                                      fg_color=BG3, hover_color=BG4, text_color=TEXT,
                                      font=F_BODY, height=32, command=_pick).pack(fill="x", padx=4, pady=2)
                ctk.CTkButton(body_f, text="+ Add Role", anchor="w",
                              fg_color="transparent", text_color=GOLD, hover_color=BG3,
                              font=F_SMALL, height=28, command=_add_role).pack(anchor="w", padx=10, pady=(0,4))

            _render_grade_system()

            # ══ PERMISSIONS accordion ═════════════════════════════════════════
            PERM_LABELS = {
                "manage_members":        "Manage Members",
                "manage_sessions":       "Manage Sessions",
                "manage_characters":     "Manage Characters",
                "view_characters":       "View Characters",
                "resolve_character_scan":"Resolve Char. Scan",
                "manage_guild_settings": "Guild Settings",
            }
            perm_state = {"open": False}
            perm_wrap  = ctk.CTkFrame(scroll, fg_color="transparent")
            perm_wrap.pack(fill="x", pady=(4, 4))

            def _render_permissions_accordion():
                for w in perm_wrap.winfo_children(): w.destroy()
                arrow    = "\u25bc" if perm_state["open"] else "\u25b6"
                perm_hdr = ctk.CTkFrame(perm_wrap, fg_color=BG3, corner_radius=6)
                perm_hdr.pack(fill="x")
                ctk.CTkLabel(perm_hdr, text=f"  {arrow}  Grade Permissions",
                             font=F_BODY_B, text_color=GOLD_LT, anchor="w").pack(side="left", padx=10, pady=8)
                def _toggle_perm():
                    perm_state["open"] = not perm_state["open"]
                    _render_permissions_accordion()
                perm_hdr.bind("<Button-1>", lambda e: _toggle_perm())
                if not perm_state["open"]: return

                perm_body = ctk.CTkFrame(perm_wrap, fg_color=BG2, corner_radius=0)
                perm_body.pack(fill="x", padx=2, pady=(0, 2))

                # Grades non-leader (colonnes)
                non_leader = [ge for ge in grades_state if ge["key"] != "leader"]
                if not non_leader:
                    ctk.CTkLabel(perm_body, text="No grades to configure.",
                                 font=F_SMALL, text_color=DIM2).pack(pady=8)
                    return

                # En-tête colonnes (noms des grades)
                hdr_row = ctk.CTkFrame(perm_body, fg_color="transparent")
                hdr_row.pack(fill="x", padx=8, pady=(6, 2))
                ctk.CTkLabel(hdr_row, text="Permission", font=F_SMALL_B,
                             text_color=DIM, width=160, anchor="w").pack(side="left")
                for ge in non_leader:
                    ctk.CTkLabel(hdr_row, text=ge["name"], font=F_SMALL_B,
                                 text_color=GOLD, width=90, anchor="center").pack(side="left", padx=4)

                ctk.CTkFrame(perm_body, fg_color=BORDER, height=1).pack(fill="x", padx=8, pady=(0, 4))

                # Lignes permissions × colonnes grades
                perm_vars = {}   # {(grade, perm_key): BooleanVar}
                for perm_key, perm_label in PERM_LABELS.items():
                    row = ctk.CTkFrame(perm_body, fg_color="transparent")
                    row.pack(fill="x", padx=8, pady=2)
                    ctk.CTkLabel(row, text=perm_label, font=F_SMALL,
                                 text_color=TEXT, width=160, anchor="w").pack(side="left")
                    for ge in non_leader:
                        gk  = ge["key"]
                        var = tk.BooleanVar(value=(gk, perm_key) in perms_state)
                        perm_vars[(gk, perm_key)] = var
                        sw = ctk.CTkSwitch(row, text="", variable=var,
                                           width=46, height=22,
                                           fg_color=BG4, progress_color=GOLD_DK,
                                           button_color=GOLD, button_hover_color=GOLD_LT)
                        sw.pack(side="left", padx=22, pady=2)
                # Stocker les vars pour _save_all
                perm_wrap._perm_vars = perm_vars

            _render_permissions_accordion()

            # ══ SESSIONS accordion ════════════════════════════════════════════
            sess_state = {"open": False}
            sess_wrap  = ctk.CTkFrame(scroll, fg_color="transparent")
            sess_wrap.pack(fill="x", pady=(4,4))

            def _render_session_accordion():
                for w in sess_wrap.winfo_children(): w.destroy()
                arrow    = "\u25bc" if sess_state["open"] else "\u25b6"
                sess_hdr = ctk.CTkFrame(sess_wrap, fg_color=BG3, corner_radius=6)
                sess_hdr.pack(fill="x")
                ctk.CTkLabel(sess_hdr, text=f"  {arrow}  Sessions",
                             font=F_BODY_B, text_color=GOLD, anchor="w").pack(side="left", padx=10, pady=8)
                def _toggle_sess():
                    sess_state["open"] = not sess_state["open"]
                    _render_session_accordion()
                sess_hdr.bind("<Button-1>", lambda e: _toggle_sess())
                if not sess_state["open"]: return
                sess_body = ctk.CTkFrame(sess_wrap, fg_color=BG2, corner_radius=0)
                sess_body.pack(fill="x", padx=2, pady=(0,2))
                ctk.CTkLabel(sess_body, text="Delete all sessions from user:",
                             font=F_SMALL, text_color=DIM, anchor="w").pack(anchor="w", padx=10, pady=(8,4))
                members_list = [m["username"] for m in g.get("members", [])]
                members_map  = {m["username"]: m["user_id"] for m in g.get("members", [])}
                del_var = tk.StringVar(value=members_list[0] if members_list else "")
                del_row = ctk.CTkFrame(sess_body, fg_color="transparent")
                del_row.pack(fill="x", padx=10, pady=(0,8))
                ctk.CTkOptionMenu(del_row, values=members_list or ["—"],
                                  variable=del_var, fg_color=BG4,
                                  button_color=GOLD_DK, text_color=TEXT,
                                  font=F_SMALL, width=200).pack(side="left", padx=(0,8))
                def _del_user_sessions():
                    uname = del_var.get()
                    uid   = members_map.get(uname)
                    if not uid: return
                    if not messagebox.askyesno("Delete Sessions",
                        f"Delete ALL sessions from {uname}?\nThis cannot be undone."): return
                    def _do():
                        try:
                            self._guild_api("DELETE", f"/guild/{guild_id}/sessions/user/{uid}",
                                            params={"token": self._guild_session_token})
                            if hasattr(self, "_members_cache"):
                                self._members_cache.pop(guild_id, None)
                            self.after(0, lambda: messagebox.showinfo("Done",
                                f"Sessions from {uname} deleted."))
                        except RuntimeError as e:
                            err_msg = str(e)
                            self.after(0, lambda msg=err_msg: messagebox.showerror("Error", msg))
                    threading.Thread(target=_do, daemon=True).start()
                ctk.CTkButton(del_row, text="\U0001f5d1 Delete Sessions",
                              width=140, height=30, fg_color="#8b0000",
                              hover_color=RED, text_color="white",
                              font=F_SMALL, corner_radius=4,
                              command=_del_user_sessions).pack(side="left")

            _render_session_accordion()

            # ── Bottom bar: Save + Delete ─────────────────────────────────────
            bot_bar = ctk.CTkFrame(self._guild_content, fg_color=BG2, height=52, corner_radius=0)
            bot_bar.pack(fill="x", side="bottom"); bot_bar.pack_propagate(False)
            ctk.CTkFrame(bot_bar, fg_color=BORDER, height=1).place(relx=0, rely=0, relwidth=1.0)

            def _save_all():
                self._guild_cache.pop(guild_id, None)
                flat   = [{"discord_role_id": r["id"], "discord_role_name": r["name"],
                           "omt_grade": gk}
                          for gk, roles in mappings_state.items() for r in roles]
                gnames = {ge["key"]: ge["name"] for ge in grades_state}
                gorder = [ge["key"] for ge in grades_state]
                # Collecter les permissions cochées
                perm_vars = getattr(perm_wrap, "_perm_vars", {})
                perms_flat = [{"grade": gk, "permission_key": pk}
                              for (gk, pk), var in perm_vars.items() if var.get()]
                def _do():
                    try:
                        self._guild_api("POST", f"/guild/{guild_id}/roles",
                                        params={"token": self._guild_session_token}, body=flat)
                        self._guild_api("PATCH", f"/guild/{guild_id}",
                                        params={"token": self._guild_session_token},
                                        body={"grade_names": gnames, "grade_order": gorder})
                        self._guild_api("POST", f"/guild/{guild_id}/permissions",
                                        params={"token": self._guild_session_token}, body=perms_flat)
                        self.after(0, lambda: messagebox.showinfo("Saved", "Guild settings saved."))
                    except RuntimeError as e:
                        err_msg = str(e)
                        self.after(0, lambda msg=err_msg: messagebox.showerror("Error", msg))
                threading.Thread(target=_do, daemon=True).start()
            gold_btn(bot_bar, "\U0001f4be  Save", _save_all, w=120, h=36).pack(side="left", padx=12, pady=8)

            def _delete_guild():
                win2 = ctk.CTkToplevel(self)
                win2.title("Delete Guild"); win2.geometry("420x220")
                win2.configure(fg_color=BG); win2.grab_set()
                win2.protocol("WM_DELETE_WINDOW", win2.destroy)
                self._set_win_icon(win2)
                ctk.CTkLabel(win2, text="\u26a0\ufe0f  Delete Guild",
                             font=F_HEAD, text_color=RED).pack(pady=(16,8))
                ctk.CTkLabel(win2, text='Type  "i want to delete my guild"  to confirm:',
                             font=F_BODY, text_color=DIM).pack(pady=(0,6))
                conf_var = tk.StringVar()
                ctk.CTkEntry(win2, textvariable=conf_var, width=320, height=34,
                             font=F_BODY, fg_color=BG2, border_color=BORDER,
                             text_color=TEXT).pack(pady=4)
                def _confirm_delete():
                    if conf_var.get().strip().lower() == "i want to delete my guild":
                        def _do():
                            try:
                                self._guild_api("DELETE", f"/guild/{guild_id}",
                                                params={"token": self._guild_session_token})
                                self.after(0, lambda: [win2.destroy(),
                                    messagebox.showinfo("Deleted","Guild deleted."),
                                    self._guild_render()])
                            except RuntimeError as e:
                                err_msg = str(e)
                                self.after(0, lambda msg=err_msg: messagebox.showerror("Error", msg))
                        threading.Thread(target=_do, daemon=True).start()
                    else:
                        messagebox.showerror("Error", "Confirmation text does not match.")
                ctk.CTkButton(win2, text="\U0001f5d1  Confirm Delete",
                              fg_color="#8b0000", hover_color=RED, text_color="white",
                              font=F_BODY_B, width=200, height=38, corner_radius=6,
                              command=_confirm_delete).pack(pady=10)
            ctk.CTkButton(bot_bar, text="\U0001f5d1  Delete Guild",
                          fg_color="transparent", hover_color="#8b0000",
                          text_color=RED, font=F_SMALL, width=130, height=36,
                          command=_delete_guild).pack(side="right", padx=12, pady=8)

        threading.Thread(target=_load, daemon=True).start()

    # ── My Profile ────────────────────────────────────────────────────────────
    def _guild_show_profile(self):
        self._guild_content_header("  \U0001f464  My Profile", pad_bottom=12)
        me = getattr(self, '_guild_me', {})
        # Avatar + username
        info = ctk.CTkFrame(self._guild_content, fg_color=BG2, corner_radius=6)
        info.pack(fill="x", padx=16, pady=4)
        self._guild_load_avatar(info, me.get("avatar"), size=64)
        ctk.CTkLabel(info, text=me.get("username","?"),
                     font=("Segoe UI",16,"bold"), text_color=TEXT).pack(side="left", padx=8, pady=12)
        ctk.CTkLabel(info, text=f"Discord ID: {me.get('id','?')}",
                     font=F_SMALL, text_color=DIM2).pack(side="left", padx=4)
        # Memberships
        ctk.CTkFrame(self._guild_content, height=10, fg_color="transparent").pack()
        ctk.CTkLabel(self._guild_content, text="  Guilds",
                     font=F_BODY_B, text_color=GOLD, anchor="w").pack(fill="x", padx=16)
        grade_colors = {"leader":"#FFD700","officer":"#C0C0C0","member":TEXT,"recruit":DIM}
        for m in me.get("memberships",[]):
            row = ctk.CTkFrame(self._guild_content, fg_color=BG2, corner_radius=4)
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=m.get("guild_name", m["guild_id"]),
                         font=F_BODY, text_color=TEXT, anchor="w").pack(side="left", padx=12, pady=6)
            ctk.CTkLabel(row, text=m["omt_grade"].upper(), font=F_SMALL,
                         text_color=grade_colors.get(m["omt_grade"],DIM)).pack(side="right", padx=12)
        ctk.CTkLabel(self._guild_content, text="More profile fields coming soon.",
                     font=F_SMALL, text_color=DIM2).pack(pady=16)

    # ── My Characters ─────────────────────────────────────────────────────────
    def _guild_show_characters(self):
        """My Characters — liste + ajout/édition/suppression de personnages."""
        self._guild_content_header("  🎮  My Characters")
        me      = getattr(self, "_guild_me", {})
        user_id = me.get("id", "")

        # Trouver la guilde active
        memberships = me.get("memberships", [])
        guild_id    = memberships[0]["guild_id"] if memberships else None

        # Couleurs et labels des types
        ROLE_COLORS = {
            "pvp": "#5B9BD5", "pvm": "#FFD700", "pk": "#E05050",
            "harvester": "#7EC88A", "crafter": "#B57FD8",
        }
        ROLE_LABELS = {
            "pvp": "PvP", "pvm": "PvM", "pk": "PK",
            "harvester": "Harv.", "crafter": "Craft.",
        }
        ACCOUNT_LABELS  = {1: "Main", 2: "Secondaire", 3: "Third", None: "Unknown"}

        # ── En-tête ───────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self._guild_content, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(hdr, text="  \U0001f3ae  My Characters",
                     font=F_HEAD, text_color=GOLD_LT, anchor="w").pack(side="left")
        add_btn = ctk.CTkButton(hdr, text="+ Add Character", width=130, height=28,
                                fg_color=GOLD_DK, hover_color=GOLD, text_color=BG,
                                font=F_SMALL, corner_radius=4,
                                command=lambda: _open_add_dialog())
        add_btn.pack(side="right")
        ctk.CTkFrame(self._guild_content, fg_color=GOLD_DK, height=1).pack(fill="x", padx=16, pady=(0, 10))

        # Zone scrollable pour la liste
        scroll = ctk.CTkScrollableFrame(self._guild_content, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8)

        status_lbl = ctk.CTkLabel(self._guild_content, text="",
                                  font=F_SMALL, text_color=DIM2)
        status_lbl.pack(pady=4)

        def _set_status(msg, color=DIM2):
            self.after(0, lambda: status_lbl.configure(text=msg, text_color=color))

        def _load():
            if not guild_id:
                _set_status("No guild selected.", DIM2)
                return
            self._guild_chars_cache = []  # reset avant rechargement
            try:
                # GET /guild/{id}/characters retourne ses propres persos
                # + ceux des autres si view_characters/manage_characters/leader/SA
                data = self._guild_api("GET", f"/guild/{guild_id}/characters",
                                       params={"token": self._guild_session_token})
                can_view_all = data.get("can_view_all", False)
                chars_by_user = data.get("characters_by_user", {})
                # Si on peut voir tous les membres, on garde tout
                # Sinon on filtre sur son propre user_id (sécurité client)
                if can_view_all:
                    all_chars = [c for lst in chars_by_user.values() for c in lst]
                else:
                    all_chars = chars_by_user.get(user_id, [])
                # Stocker pour le renommage de compte
                self._guild_chars_cache = all_chars
                self.after(0, lambda: _render(all_chars, can_view_all))
            except RuntimeError as e:
                err = str(e)
                self.after(0, lambda msg=err: _set_status(f"Error: {msg}", RED))

        def _render(chars, can_view_all=False):
            for w in scroll.winfo_children(): w.destroy()
            if not chars:
                ctk.CTkLabel(scroll, text="No characters registered yet.",
                             font=F_BODY, text_color=DIM2).pack(pady=20)
                return

            # Si on voit tous les membres, grouper par user puis par account
            if can_view_all:
                # Grouper d'abord par user_id
                by_user: dict = {}
                for c in chars:
                    by_user.setdefault(c.get("user_id", "?"), []).append(c)
                for uid, user_chars in by_user.items():
                    # En-tête membre
                    ctk.CTkLabel(scroll, text=f"  👤 {uid}",
                                 font=F_BODY_B, text_color=GOLD_LT,
                                 anchor="w").pack(fill="x", padx=4, pady=(10, 2))
                    ctk.CTkFrame(scroll, fg_color=GOLD_DK, height=1).pack(fill="x", padx=4, pady=(0, 4))
                    _render_accounts(scroll, user_chars)
                return

        def _render_accounts(parent, chars):
            # Grouper par account_number (None = Unknown)
            accounts = {}
            for c in chars:
                acc = c.get("account_number")
                # Normaliser : si account_number est 0 ou absent, mettre None
                if acc not in (1, 2, 3):
                    acc = None
                accounts.setdefault(acc, []).append(c)

            # Ordre : 1 (Main), 2 (Secondaire), 3 (Third), None (Unknown)
            order = [k for k in (1, 2, 3, None) if k in accounts]

            acc_open = {}  # {acc_num: bool}

            def _render_acc(acc_num):
                # Nettoyer le frame du compte
                frame_key = f"acc_{acc_num}"
                if not hasattr(parent, "_acc_frames"):
                    parent._acc_frames = {}
                if frame_key in parent._acc_frames:
                    parent._acc_frames[frame_key].destroy()
                acc_wrap = ctk.CTkFrame(parent, fg_color="transparent")
                acc_wrap.pack(fill="x", padx=4, pady=(4, 0))
                parent._acc_frames[frame_key] = acc_wrap

                acc_chars = accounts[acc_num]
                base_label = ACCOUNT_LABELS.get(acc_num, f"Account {acc_num}")
                # Label personnalisé si défini
                custom = acc_chars[0].get("account_label") if acc_chars else None
                acc_label = custom or base_label
                is_open = acc_open.get(acc_num, True)  # ouvert par défaut

                # En-tête accordéon
                arrow = "\u25bc" if is_open else "\u25b6"
                hdr_acc = ctk.CTkFrame(acc_wrap, fg_color=BG3, corner_radius=4)
                hdr_acc.pack(fill="x")
                ctk.CTkLabel(hdr_acc, text=f"  {arrow}  {acc_label}  ({len(acc_chars)})",
                             font=F_BODY_B, text_color=GOLD, anchor="w").pack(side="left", padx=8, pady=5)

                def _toggle(an=acc_num):
                    acc_open[an] = not acc_open.get(an, True)
                    _render_acc(an)
                hdr_acc.bind("<Button-1>", lambda e, an=acc_num: _toggle(an))

                if acc_num is not None:
                    ctk.CTkButton(hdr_acc, text="✏", width=22, height=22,
                                  fg_color="transparent", hover_color=BG4,
                                  text_color=DIM, font=F_SMALL,
                                  command=lambda an=acc_num, al=acc_label: _rename_account(an, al)
                                  ).pack(side="left", padx=2)

                if not is_open:
                    return

                # Corps accordéon
                body_acc = ctk.CTkFrame(acc_wrap, fg_color="transparent")
                body_acc.pack(fill="x", padx=2, pady=(2, 4))
                for c in acc_chars:
                    _draw_char_row(body_acc, c)

            for acc_num in order:
                _render_acc(acc_num)

            # Grouper par account_number
            accounts = {}
            for c in chars:
                acc = c.get("account_number", 1)
                accounts.setdefault(acc, []).append(c)

            for acc_num in sorted(accounts.keys()):
                acc_chars = accounts[acc_num]
                # Label du compte
                # Prendre le label du premier personnage du compte (tous ont le même)
                acc_label = acc_chars[0].get("account_label") or ACCOUNT_DEFAULT.get(acc_num, f"Account {acc_num}")
                hdr_acc = ctk.CTkFrame(scroll, fg_color="transparent")
                hdr_acc.pack(fill="x", padx=4, pady=(10, 2))
                ctk.CTkLabel(hdr_acc, text=f"  {acc_label}",
                             font=F_BODY_B, text_color=GOLD, anchor="w").pack(side="left")
                ctk.CTkButton(hdr_acc, text="✏", width=24, height=20,
                              fg_color="transparent", hover_color=BG3,
                              text_color=DIM, font=F_SMALL,
                              command=lambda an=acc_num, al=acc_label: _rename_account(an, al)
                              ).pack(side="left", padx=2)
                ctk.CTkFrame(scroll, fg_color=BG3, height=1).pack(fill="x", padx=4, pady=(0, 4))

                for c in acc_chars:
                    _draw_char_row(scroll, c)

        def _draw_char_row(parent, c):
            row = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=4)
            row.pack(fill="x", padx=4, pady=2)

            # Nom du personnage
            ctk.CTkLabel(row, text=c["name"], font=F_BODY,
                         text_color=TEXT, anchor="w", width=160).pack(side="left", padx=10, pady=6)

            # Tags de type (multi)
            tag_frame = ctk.CTkFrame(row, fg_color="transparent")
            tag_frame.pack(side="left", padx=4)
            for role in c.get("roles", []):
                color = ROLE_COLORS.get(role, DIM)
                label = ROLE_LABELS.get(role, role.capitalize())
                ctk.CTkLabel(tag_frame, text=label, font=F_SMALL,
                             text_color=BG, fg_color=color,
                             corner_radius=4, width=44, height=18).pack(side="left", padx=2)

            # Boutons Edit / Delete
            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.pack(side="right", padx=6)
            ctk.CTkButton(btn_frame, text="✏ Edit", width=64, height=24,
                          fg_color=BG3, hover_color=BG4, text_color=GOLD,
                          font=F_SMALL, corner_radius=4,
                          command=lambda ch=c: _open_edit_dialog(ch)).pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text="🗑", width=28, height=24,
                          fg_color="transparent", hover_color="#5a1a1a",
                          text_color=RED, font=F_SMALL, corner_radius=4,
                          command=lambda ch=c: _confirm_delete(ch)).pack(side="left", padx=2)

        # ── Dialogue ajout ────────────────────────────────────────────────────
        # Dialogues délégués aux méthodes de classe
        def _open_add_dialog():
            self._guild_char_dialog_add(guild_id, _load)

        def _open_edit_dialog(c):
            self._guild_char_dialog_edit(guild_id, c, _load)

        def _rename_account(acc_num, current_label):
            self._guild_char_dialog_rename(guild_id, acc_num, current_label, _load)

        def _confirm_delete(c):
            self._guild_char_confirm_delete(guild_id, c, _load, _set_status)

        # ── Lancement initial ──────────────────────────────────────────────────
        if guild_id:
            threading.Thread(target=_load, daemon=True).start()
        else:
            ctk.CTkLabel(scroll, text="Join a guild to manage characters.",
                         font=F_BODY, text_color=DIM2).pack(pady=20)

    # ── GU Edit — SuperAdmin guild manager ────────────────────────────────────
    # ── Character dialogs — extraits de _guild_show_characters ──────────────────

    def _guild_char_dialog_add(self, guild_id: str, on_done):
        """Dialogue d'ajout de personnage — méthode de classe pour maintenabilité."""
        ROLE_COLORS = {"pvp":"#5B9BD5","pvm":"#FFD700","pk":"#E05050","harvester":"#7EC88A","crafter":"#B57FD8"}
        ROLE_LABELS = {"pvp":"PvP","pvm":"PvM","pk":"PK","harvester":"Harv.","crafter":"Craft."}
        win = ctk.CTkToplevel(self)
        win.title("Add Character"); win.geometry("420x400")
        win.configure(fg_color=BG); win.grab_set()
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.after(250, lambda: self._set_win_icon(win))
        ctk.CTkLabel(win, text="  Add Character", font=F_HEAD,
                     text_color=GOLD_LT, anchor="w").pack(fill="x", padx=16, pady=(14,4))
        ctk.CTkFrame(win, fg_color=GOLD_DK, height=1).pack(fill="x", padx=16, pady=(0,12))
        ctk.CTkLabel(win, text="Character name", font=F_SMALL,
                     text_color=DIM, anchor="w").pack(fill="x", padx=16)
        name_var = ctk.StringVar()
        ctk.CTkEntry(win, textvariable=name_var, placeholder_text="ExactName (case-sensitive)",
                     font=F_BODY).pack(fill="x", padx=16, pady=(2,8))
        ctk.CTkLabel(win, text="Account", font=F_SMALL,
                     text_color=DIM, anchor="w").pack(fill="x", padx=16)
        acc_var = ctk.StringVar(value="Main")
        ctk.CTkSegmentedButton(win, values=["Main","Secondaire","Third"], variable=acc_var,
                               fg_color=BG3, selected_color=GOLD_DK, selected_hover_color=GOLD,
                               text_color=TEXT).pack(padx=16, pady=(2,8), anchor="w")
        ctk.CTkLabel(win, text="Type(s)", font=F_SMALL,
                     text_color=DIM, anchor="w").pack(fill="x", padx=16)
        role_frame = ctk.CTkFrame(win, fg_color="transparent")
        role_frame.pack(fill="x", padx=16, pady=(2,12))
        row1 = ctk.CTkFrame(role_frame, fg_color="transparent"); row1.pack(fill="x", pady=(0,4))
        row2 = ctk.CTkFrame(role_frame, fg_color="transparent"); row2.pack(fill="x")
        role_rows = {"pvp":row1,"pvm":row1,"pk":row1,"harvester":row2,"crafter":row2}
        role_vars = {}
        for role, label in ROLE_LABELS.items():
            var = ctk.BooleanVar(value=False); role_vars[role] = var
            ctk.CTkCheckBox(role_rows[role], text=label, variable=var,
                            text_color=ROLE_COLORS[role], checkmark_color=ROLE_COLORS[role],
                            fg_color=BG3, hover_color=BG4, font=F_SMALL).pack(side="left", padx=6)
        err_lbl = ctk.CTkLabel(win, text="", font=F_SMALL, text_color=RED); err_lbl.pack()
        def _do_add():
            name = name_var.get().strip()
            if not name: err_lbl.configure(text="Name is required."); return
            acc  = {"Main":1,"Secondaire":2,"Third":3}.get(acc_var.get(), 1)
            roles = [r for r, v in role_vars.items() if v.get()]
            def _req():
                try:
                    self._guild_api("POST", f"/guild/{guild_id}/characters",
                                    body={"name": name, "account_number": acc, "roles": roles},
                                    params={"token": self._guild_session_token})
                    self.after(0, lambda: win.winfo_exists() and [win.destroy(), threading.Thread(target=on_done, daemon=True).start()])
                except RuntimeError as e:
                    msg = str(e)
                    self.after(0, lambda m=msg: win.winfo_exists() and err_lbl.configure(text=m))
            threading.Thread(target=_req, daemon=True).start()
        ctk.CTkButton(win, text="Add Character", fg_color=GOLD_DK, hover_color=GOLD,
                      text_color=BG, font=F_BODY_B, command=_do_add).pack(padx=16, pady=4, fill="x")

    def _guild_char_dialog_edit(self, guild_id: str, c: dict, on_done):
        """Dialogue d'édition de personnage."""
        ROLE_COLORS = {"pvp":"#5B9BD5","pvm":"#FFD700","pk":"#E05050","harvester":"#7EC88A","crafter":"#B57FD8"}
        ROLE_LABELS = {"pvp":"PvP","pvm":"PvM","pk":"PK","harvester":"Harv.","crafter":"Craft."}
        win = ctk.CTkToplevel(self)
        win.title("Edit Character"); win.geometry("420x400")
        win.configure(fg_color=BG); win.grab_set()
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.after(250, lambda: self._set_win_icon(win))
        ctk.CTkLabel(win, text="  Edit Character", font=F_HEAD,
                     text_color=GOLD_LT, anchor="w").pack(fill="x", padx=16, pady=(14,4))
        ctk.CTkFrame(win, fg_color=GOLD_DK, height=1).pack(fill="x", padx=16, pady=(0,12))
        ctk.CTkLabel(win, text="Character name", font=F_SMALL,
                     text_color=DIM, anchor="w").pack(fill="x", padx=16)
        name_var = ctk.StringVar(value=c["name"])
        ctk.CTkEntry(win, textvariable=name_var, font=F_BODY).pack(fill="x", padx=16, pady=(2,8))
        ctk.CTkLabel(win, text="Account", font=F_SMALL,
                     text_color=DIM, anchor="w").pack(fill="x", padx=16)
        acc_var = ctk.StringVar(value={1:"Main",2:"Secondaire",3:"Third"}.get(c.get("account_number",1),"Main"))
        ctk.CTkSegmentedButton(win, values=["Main","Secondaire","Third"], variable=acc_var,
                               fg_color=BG3, selected_color=GOLD_DK, selected_hover_color=GOLD,
                               text_color=TEXT).pack(padx=16, pady=(2,8), anchor="w")
        ctk.CTkLabel(win, text="Type(s)", font=F_SMALL,
                     text_color=DIM, anchor="w").pack(fill="x", padx=16)
        role_frame = ctk.CTkFrame(win, fg_color="transparent")
        role_frame.pack(fill="x", padx=16, pady=(2,12))
        row1 = ctk.CTkFrame(role_frame, fg_color="transparent"); row1.pack(fill="x", pady=(0,4))
        row2 = ctk.CTkFrame(role_frame, fg_color="transparent"); row2.pack(fill="x")
        role_rows = {"pvp":row1,"pvm":row1,"pk":row1,"harvester":row2,"crafter":row2}
        current_roles = c.get("roles", []); role_vars = {}
        for role, label in ROLE_LABELS.items():
            var = ctk.BooleanVar(value=role in current_roles); role_vars[role] = var
            ctk.CTkCheckBox(role_rows[role], text=label, variable=var,
                            text_color=ROLE_COLORS[role], checkmark_color=ROLE_COLORS[role],
                            fg_color=BG3, hover_color=BG4, font=F_SMALL).pack(side="left", padx=6)
        err_lbl = ctk.CTkLabel(win, text="", font=F_SMALL, text_color=RED); err_lbl.pack()
        def _do_edit():
            name = name_var.get().strip()
            if not name: err_lbl.configure(text="Name is required."); return
            acc  = {"Main":1,"Secondaire":2,"Third":3}.get(acc_var.get(), 1)
            roles = [r for r, v in role_vars.items() if v.get()]
            def _req():
                try:
                    self._guild_api("PATCH", f"/guild/{guild_id}/characters/{c['id']}",
                                    body={"name": name, "account_number": acc},
                                    params={"token": self._guild_session_token})
                    self._guild_api("PUT", f"/guild/{guild_id}/characters/{c['id']}/roles",
                                    body={"roles": roles},
                                    params={"token": self._guild_session_token})
                    self.after(0, lambda: win.winfo_exists() and [win.destroy(), threading.Thread(target=on_done, daemon=True).start()])
                except RuntimeError as e:
                    msg = str(e)
                    self.after(0, lambda m=msg: win.winfo_exists() and err_lbl.configure(text=m))
            threading.Thread(target=_req, daemon=True).start()
        ctk.CTkButton(win, text="Save Changes", fg_color=GOLD_DK, hover_color=GOLD,
                      text_color=BG, font=F_BODY_B, command=_do_edit).pack(padx=16, pady=4, fill="x")

    def _guild_char_dialog_rename(self, guild_id: str, acc_num: int, current_label: str, on_done):
        """Dialogue de renommage de compte."""
        win = ctk.CTkToplevel(self)
        win.title("Rename Account"); win.geometry("340x180")
        win.configure(fg_color=BG); win.grab_set()
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.after(250, lambda: self._set_win_icon(win))
        ctk.CTkLabel(win, text=f"  Rename Account {acc_num}", font=F_HEAD,
                     text_color=GOLD_LT, anchor="w").pack(fill="x", padx=16, pady=(14,4))
        ctk.CTkFrame(win, fg_color=GOLD_DK, height=1).pack(fill="x", padx=16, pady=(0,12))
        lbl_var = ctk.StringVar(value="" if current_label in ("Main","Secondaire","Third","Account 1","Account 2","Account 3") else current_label)
        ctk.CTkEntry(win, textvariable=lbl_var,
                     placeholder_text=f"Account {acc_num} label (leave empty to reset)",
                     font=F_BODY).pack(fill="x", padx=16, pady=(0,8))
        err_lbl = ctk.CTkLabel(win, text="", font=F_SMALL, text_color=RED); err_lbl.pack()
        def _do_rename():
            new_label = lbl_var.get().strip() or None
            chars_to_update = [c for c in getattr(self, "_guild_chars_cache", [])
                               if c.get("account_number") == acc_num]
            def _req():
                try:
                    for ch in chars_to_update:
                        self._guild_api("PATCH", f"/guild/{guild_id}/characters/{ch['id']}",
                                        body={"account_label": new_label or ""},
                                        params={"token": self._guild_session_token})
                    self.after(0, lambda: win.winfo_exists() and [win.destroy(), threading.Thread(target=on_done, daemon=True).start()])
                except RuntimeError as e:
                    msg = str(e)
                    self.after(0, lambda m=msg: win.winfo_exists() and err_lbl.configure(text=m))
            threading.Thread(target=_req, daemon=True).start()
        ctk.CTkButton(win, text="Rename", fg_color=GOLD_DK, hover_color=GOLD,
                      text_color=BG, font=F_BODY_B, command=_do_rename).pack(padx=16, pady=4, fill="x")

    def _guild_char_confirm_delete(self, guild_id: str, c: dict, on_done, set_status=None):
        """Confirmation de suppression de personnage."""
        from tkinter import messagebox
        if not messagebox.askyesno("Delete Character",
                f"Delete '{c['name']}'?\nThis cannot be undone."):
            return
        def _req():
            try:
                self._guild_api("DELETE", f"/guild/{guild_id}/characters/{c['id']}",
                                params={"token": self._guild_session_token})
                self.after(0, lambda: threading.Thread(target=on_done, daemon=True).start())
            except RuntimeError as e:
                err = str(e)
                if set_status:
                    self.after(0, lambda msg=err: set_status(f"Error: {msg}", RED))
                else:
                    self.after(0, lambda msg=err: messagebox.showerror("Error", msg))
        threading.Thread(target=_req, daemon=True).start()

    # ── SuperAdmin Panel — interface séparée, indépendante du système Guild ──────
    def _superadmin_panel(self):
        """Panneau SuperAdmin — accessible via bouton ⚡ dans la nav principale.
        Complètement séparé du système de guilde.
        """
        win = ctk.CTkToplevel(self)
        win.title("⚡ SuperAdmin Panel")
        win.geometry("820x600")
        win.configure(fg_color=BG)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.after(250, lambda: self._set_win_icon(win))

        # ── En-tête ───────────────────────────────────────────────────────────
        ctk.CTkLabel(win, text="⚡  SuperAdmin Panel",
                     font=("Georgia", 16, "bold"), text_color="#ff4444").pack(pady=(14, 4))
        ctk.CTkFrame(win, fg_color=GOLD_DK, height=1).pack(fill="x", padx=20, pady=(0, 0))

        # ── Tabs ──────────────────────────────────────────────────────────────
        tab_bar = ctk.CTkFrame(win, fg_color="transparent")
        tab_bar.pack(fill="x", padx=12, pady=6)

        content = ctk.CTkScrollableFrame(win, fg_color=BG2)
        content.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        current_tab = {"name": None}

        def _activate_tab(name, load_fn):
            for w in tab_bar.winfo_children():
                if hasattr(w, "_tab_name"):
                    w.configure(fg_color=BG3 if w._tab_name == name else "transparent",
                                text_color=GOLD if w._tab_name == name else DIM)
            current_tab["name"] = name
            for w in content.winfo_children(): w.destroy()
            load_fn()

        def _make_tab(label, load_fn):
            b = ctk.CTkButton(tab_bar, text=label, width=120, height=30,
                              fg_color="transparent", hover_color=BG3,
                              text_color=DIM, font=F_SMALL,
                              command=lambda: _activate_tab(label, load_fn))
            b._tab_name = label
            b.pack(side="left", padx=3)
            return b

        # ── TAB : Users ───────────────────────────────────────────────────────
        def _load_users():
            ctk.CTkLabel(content, text="Loading...", text_color=DIM2,
                         font=F_BODY).pack(pady=20)
            def _fetch():
                try:
                    data = self._guild_api("GET", "/admin/users",
                                           params={"token": self._guild_session_token})
                    def _safe():
                        if not win.winfo_exists(): return
                        _render_users(data)
                    self.after(0, _safe)
                except RuntimeError as e:
                    err = str(e)
                    self.after(0, lambda m=err: ctk.CTkLabel(
                        content, text=f"Error: {m}", text_color=RED,
                        font=F_SMALL).pack(pady=8) if win.winfo_exists() else None)
            threading.Thread(target=_fetch, daemon=True).start()

        def _render_users(users):
            for w in content.winfo_children(): w.destroy()
            if not users:
                ctk.CTkLabel(content, text="No users.", text_color=DIM2,
                             font=F_BODY).pack(pady=20)
                return
            # En-tête
            hdr = ctk.CTkFrame(content, fg_color="transparent")
            hdr.pack(fill="x", padx=4, pady=(4, 2))
            ctk.CTkLabel(hdr, text="Username", font=F_SMALL_B, text_color=DIM,
                         width=200, anchor="w").pack(side="left", padx=6)
            ctk.CTkLabel(hdr, text="Discord ID", font=F_SMALL_B, text_color=DIM,
                         width=160, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="SA", font=F_SMALL_B, text_color=DIM,
                         width=40, anchor="center").pack(side="left")
            ctk.CTkFrame(content, fg_color=BORDER, height=1).pack(fill="x", padx=4, pady=(0, 4))

            for u in users:
                row = ctk.CTkFrame(content, fg_color=BG3, corner_radius=3)
                row.pack(fill="x", padx=4, pady=1)
                uid  = u.get("id", "?")
                uname = u.get("username", "?")
                is_sa = u.get("is_superadmin", False)
                ctk.CTkLabel(row, text=uname, font=F_BODY, text_color=TEXT,
                             width=200, anchor="w").pack(side="left", padx=6, pady=4)
                ctk.CTkLabel(row, text=uid, font=F_SMALL, text_color=DIM2,
                             width=160, anchor="w").pack(side="left")
                # Toggle SuperAdmin
                sa_var = tk.BooleanVar(value=is_sa)
                def _toggle_sa(uid2=uid, var=sa_var):
                    new_val = var.get()
                    def _do():
                        try:
                            self._guild_api("PATCH", f"/admin/users/{uid2}",
                                            params={"token": self._guild_session_token},
                                            body={"is_superadmin": new_val})
                        except RuntimeError as e:
                            err = str(e)
                            self.after(0, lambda m=err: messagebox.showerror("Error", m))
                    threading.Thread(target=_do, daemon=True).start()
                ctk.CTkSwitch(row, text="", variable=sa_var, width=46, height=22,
                              fg_color=BG4, progress_color="#ff4444",
                              button_color=GOLD, button_hover_color=GOLD_LT,
                              command=_toggle_sa).pack(side="left", padx=6)
                # Supprimer
                def _del_user(uid2=uid, uname2=uname):
                    if not messagebox.askyesno("Delete User",
                            f"Delete {uname2}?\nThis cannot be undone."): return
                    def _do():
                        try:
                            self._guild_api("DELETE", f"/admin/users/{uid2}",
                                            params={"token": self._guild_session_token})
                            self.after(0, _load_users)
                        except RuntimeError as e:
                            err = str(e)
                            self.after(0, lambda m=err: messagebox.showerror("Error", m))
                    threading.Thread(target=_do, daemon=True).start()
                ctk.CTkButton(row, text="🗑", width=28, height=26,
                              fg_color="transparent", hover_color="#5a1a1a",
                              text_color=RED, font=F_SMALL, corner_radius=4,
                              command=_del_user).pack(side="right", padx=6)

        # ── TAB : Guilds ──────────────────────────────────────────────────────
        def _load_guilds():
            ctk.CTkLabel(content, text="Loading...", text_color=DIM2,
                         font=F_BODY).pack(pady=20)
            def _fetch():
                try:
                    data = self._guild_api("GET", "/admin/guilds",
                                           params={"token": self._guild_session_token})
                    def _safe():
                        if not win.winfo_exists(): return
                        _render_guilds(data)
                    self.after(0, _safe)
                except RuntimeError as e:
                    err = str(e)
                    self.after(0, lambda m=err: ctk.CTkLabel(
                        content, text=f"Error: {m}", text_color=RED,
                        font=F_SMALL).pack(pady=8) if win.winfo_exists() else None)
            threading.Thread(target=_fetch, daemon=True).start()

        def _render_guilds(guilds):
            for w in content.winfo_children(): w.destroy()
            if not guilds:
                ctk.CTkLabel(content, text="No guilds.", text_color=DIM2,
                             font=F_BODY).pack(pady=20)
                return
            for g in guilds:
                row = ctk.CTkFrame(content, fg_color=BG3, corner_radius=4)
                row.pack(fill="x", padx=4, pady=2)
                info = ctk.CTkFrame(row, fg_color="transparent")
                info.pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(info, text=g.get("name", "?"), font=F_BODY_B,
                             text_color=GOLD, anchor="w").pack(fill="x", padx=10, pady=(4, 0))
                ctk.CTkLabel(info,
                             text=f"ID: {g['id']}  |  Owner: {g.get('owner_id','?')}  |  Members: {g.get('member_count',0)}",
                             font=F_SMALL, text_color=DIM2, anchor="w").pack(fill="x", padx=10, pady=(0, 4))
                def _del_guild(gid=g["id"], gname=g.get("name","?")):
                    if not messagebox.askyesno("Delete Guild",
                            f"Delete '{gname}'?\nThis will remove all members and kick the bot."): return
                    def _do():
                        try:
                            self._guild_api("DELETE", f"/guild/{gid}/admin-delete",
                                            params={"token": self._guild_session_token})
                            self.after(0, lambda: [
                                messagebox.showinfo("Done", f"'{gname}' deleted."),
                                _load_guilds()
                            ])
                        except RuntimeError as e:
                            err = str(e)
                            self.after(0, lambda m=err: messagebox.showerror("Error", m))
                    threading.Thread(target=_do, daemon=True).start()
                ctk.CTkButton(row, text="🗑 Delete", width=90, height=32,
                              fg_color="#8b0000", hover_color=RED, text_color="white",
                              font=F_SMALL, corner_radius=4,
                              command=_del_guild).pack(side="right", padx=8, pady=6)

        # ── TAB : Stats ───────────────────────────────────────────────────────
        def _load_stats():
            ctk.CTkLabel(content, text="Loading...", text_color=DIM2,
                         font=F_BODY).pack(pady=20)
            def _fetch():
                try:
                    data = self._guild_api("GET", "/admin/stats",
                                           params={"token": self._guild_session_token})
                    def _safe():
                        if not win.winfo_exists(): return
                        _render_stats(data)
                    self.after(0, _safe)
                except RuntimeError as e:
                    err = str(e)
                    self.after(0, lambda m=err: ctk.CTkLabel(
                        content, text=f"Error: {m}", text_color=RED,
                        font=F_SMALL).pack(pady=8) if win.winfo_exists() else None)
            threading.Thread(target=_fetch, daemon=True).start()

        def _render_stats(data):
            for w in content.winfo_children(): w.destroy()
            grid = ctk.CTkFrame(content, fg_color="transparent")
            grid.pack(fill="x", padx=8, pady=8)
            items = list(data.items())
            for idx, (k, v) in enumerate(items):
                cell = ctk.CTkFrame(grid, fg_color=BG3, corner_radius=6)
                cell.grid(row=idx//2, column=idx%2, padx=6, pady=4, sticky="ew")
                grid.columnconfigure(0, weight=1)
                grid.columnconfigure(1, weight=1)
                ctk.CTkLabel(cell, text=str(k).replace("_"," ").title(),
                             font=F_SMALL, text_color=DIM2, anchor="w").pack(fill="x", padx=10, pady=(6,0))
                ctk.CTkLabel(cell, text=str(v),
                             font=("Segoe UI", 20, "bold"), text_color=GOLD,
                             anchor="w").pack(fill="x", padx=10, pady=(0,6))

        # ── TAB : Official Server ─────────────────────────────────────────────
        def _load_official_server():
            for w in content.winfo_children(): w.destroy()
            ctk.CTkLabel(content, text="  🌐  Official Discord Server",
                         font=F_HEAD, text_color=GOLD_LT, anchor="w").pack(fill="x", padx=8, pady=(8,4))
            ctk.CTkLabel(content,
                         text="Configure the official OMT Discord server and feedback channels.",
                         font=F_SMALL, text_color=DIM2, anchor="w").pack(fill="x", padx=8, pady=(0,12))

            # Serveur Discord
            ctk.CTkLabel(content, text="Discord Server", font=F_SMALL_B,
                         text_color=DIM, anchor="w").pack(fill="x", padx=8)
            server_var = ctk.StringVar(value="Loading...")
            server_menu = ctk.CTkOptionMenu(content, variable=server_var,
                                             values=["Loading..."],
                                             fg_color=BG3, button_color=GOLD_DK,
                                             text_color=TEXT, font=F_SMALL, width=300)
            server_menu.pack(anchor="w", padx=8, pady=(2, 12))

            # Salons feedback
            channel_labels = ["Bug", "Suggestion", "Location", "Other"]
            channel_vars   = {l: ctk.StringVar(value="—") for l in channel_labels}
            channel_menus  = {}

            ctk.CTkFrame(content, fg_color=BORDER, height=1).pack(fill="x", padx=8, pady=(0,8))
            ctk.CTkLabel(content, text="Feedback Channels", font=F_SMALL_B,
                         text_color=DIM, anchor="w").pack(fill="x", padx=8, pady=(0,6))

            for lbl in channel_labels:
                row = ctk.CTkFrame(content, fg_color="transparent")
                row.pack(fill="x", padx=8, pady=2)
                ctk.CTkLabel(row, text=lbl, font=F_SMALL, text_color=TEXT,
                             width=90, anchor="w").pack(side="left")
                m = ctk.CTkOptionMenu(row, variable=channel_vars[lbl],
                                      values=["—"], fg_color=BG3,
                                      button_color=GOLD_DK, text_color=TEXT,
                                      font=F_SMALL, width=220)
                m.pack(side="left", padx=4)
                channel_menus[lbl] = m

            err_lbl = ctk.CTkLabel(content, text="", font=F_SMALL, text_color=RED)
            err_lbl.pack(pady=4)

            servers_map = {}   # {name: id}
            channels_map = {}  # {name: id}

            def _load_servers():
                def _fetch():
                    try:
                        data = self._guild_api("GET", "/guild/discord-servers",
                                               params={"token": self._guild_session_token})
                        admin = data.get("admin_servers", [])
                        def _safe():
                            if not win.winfo_exists(): return
                            servers_map.clear()
                            for s in admin:
                                servers_map[s["name"]] = s["id"]
                            names = list(servers_map.keys()) or ["—"]
                            server_menu.configure(values=names)
                            server_var.set(names[0])
                            server_menu.configure(command=lambda n: _load_channels(servers_map[n]))
                            if names[0] != "—":
                                _load_channels(servers_map[names[0]])
                        self.after(0, _safe)
                    except RuntimeError as e:
                        err = str(e)
                        self.after(0, lambda m=err: err_lbl.configure(
                            text=f"Error: {m}") if win.winfo_exists() else None)
                threading.Thread(target=_fetch, daemon=True).start()

            def _load_channels(server_id):
                def _fetch():
                    try:
                        data = self._guild_api("GET", f"/guild/discord-channels/{server_id}", params={"token": self._guild_session_token})
                        channels = data.get("channels", [])
                        def _safe():
                            if not win.winfo_exists(): return
                            channels_map.clear()
                            channels_map["—"] = None
                            for c in channels:
                                channels_map[c["name"]] = c["id"]
                            names = ["—"] + [c["name"] for c in channels]
                            for m in channel_menus.values():
                                m.configure(values=names)
                        self.after(0, _safe)
                    except RuntimeError as e:
                        err = str(e)
                        self.after(0, lambda m=err: err_lbl.configure(
                            text=f"Channels error: {m}") if win.winfo_exists() else None)
                threading.Thread(target=_fetch, daemon=True).start()

            def _save_official():
                server_name = server_var.get()
                server_id   = servers_map.get(server_name)
                if not server_id:
                    err_lbl.configure(text="Select a server first.")
                    return
                body = {
                    "channel_bug":        channels_map.get(channel_vars["Bug"].get()),
                    "channel_suggestion": channels_map.get(channel_vars["Suggestion"].get()),
                    "channel_location":   channels_map.get(channel_vars["Location"].get()),
                    "channel_other":      channels_map.get(channel_vars["Other"].get()),
                }
                def _do():
                    try:
                        self._guild_api("PUT", f"/guild/{server_id}/feedback-config",
                                        params={"token": self._guild_session_token},
                                        body=body)
                        self.after(0, lambda: messagebox.showinfo("Saved",
                            "Official server configuration saved.") if win.winfo_exists() else None)
                    except RuntimeError as e:
                        err = str(e)
                        self.after(0, lambda m=err: err_lbl.configure(
                            text=f"Error: {m}") if win.winfo_exists() else None)
                threading.Thread(target=_do, daemon=True).start()

            gold_btn(content, "💾  Save", _save_official, w=140, h=36).pack(
                anchor="w", padx=8, pady=10)
            _load_servers()

        # ── Création des tabs ─────────────────────────────────────────────────
        _make_tab("Users",           _load_users)
        _make_tab("Guilds",          _load_guilds)
        _make_tab("Stats",           _load_stats)
        _make_tab("Official Server", _load_official_server)

        # Activer Users par défaut
        _activate_tab("Users", _load_users)

    def _upload_selected_to_guild(self):
        """Upload selected sessions to guild."""
        if not self._guild_session_token:
            messagebox.showwarning("Not connected", "Connect to Guild first.")
            return
        selected = self._selected()
        if not selected:
            messagebox.showwarning("No selection", "Select sessions to upload.")
            return
        guild_id = getattr(self, "_guild_active_id", None)
        if not guild_id:
            memberships = getattr(self, "_guild_me", {}).get("memberships", [])
            guild_id = memberships[0]["guild_id"] if memberships else None
        if not guild_id:
            messagebox.showwarning("No guild", "You are not in a guild.")
            return
        serialized = []
        for s in selected:
            ser = dict(s)
            if hasattr(ser.get("start"), "isoformat"): ser["start"] = ser["start"].isoformat()
            if hasattr(ser.get("end"),   "isoformat"): ser["end"]   = ser["end"].isoformat()
            serialized.append(ser)
        def _do():
            try:
                r = self._guild_api("POST", f"/guild/{guild_id}/sessions/upload",
                                    params={"token": self._guild_session_token},
                                    body={"sessions": serialized})
                added = r.get("added", 0); skipped = r.get("skipped", 0)
                if not hasattr(self, "_guild_uploaded_starts"):
                    self._guild_uploaded_starts = set()
                for s in serialized:
                    if s.get("start"): self._guild_uploaded_starts.add(s["start"])
                self.after(0, lambda: messagebox.showinfo(
                    "Upload Guild", f"Uploaded {added} sessions ({skipped} already existed)."))
            except RuntimeError as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: messagebox.showerror("Error", msg))
        threading.Thread(target=_do, daemon=True).start()

    def _on_upload_all_toggle(self):
        """Handle Upload All Guild Sessions checkbox toggle."""
        val = self._upload_all_var.get()
        self.settings["guild_upload_all"] = val
        save_json(SETTINGS_F, self.settings)
        if val and self._guild_session_token:
            if messagebox.askyesno("Upload All",
                f"Upload all {len(self.sessions)} sessions to guild now?"):
                self._guild_upload_all()

    # ── Session Upload helpers ─────────────────────────────────────────────────
    def _draw_upload_cell(self, row, s):
        """Draw upload icon button for a session row."""
        cw   = self.COLS[1][3]
        gap  = self.COL_GAP
        cell = ctk.CTkFrame(row, fg_color="transparent", width=cw, height=28)
        cell.pack(side="left", padx=(gap,0)); cell.pack_propagate(False)
        # Determine upload state
        s_start = s.get("start","")
        if hasattr(s_start, "isoformat"): s_start = s_start.isoformat()
        uploaded = s_start in getattr(self, "_guild_uploaded_starts", set())
        # Load icon
        if not hasattr(self, "_gupload_ph"):
            ph = load_pil("gupload.png", (24,24), transparent=True)
            self._gupload_ph = ImageTk.PhotoImage(ph) if ph else None
            if self._gupload_ph: self._keep(self._gupload_ph)
        ico = self._gupload_ph
        color = GOLD if uploaded else DIM2
        btn = ctk.CTkButton(cell, image=ico if ico else None,
                             text="" if ico else "↑",
                             width=cw-4, height=24,
                             fg_color="transparent",
                             text_color=color,
                             hover_color=BG4,
                             command=lambda sv=s_start, sess=s, b=None: self._toggle_upload(sv, sess))
        btn.pack(expand=True)
        # Store ref for state refresh
        if not hasattr(self, "_upload_btns"): self._upload_btns = {}
        self._upload_btns[s_start] = (btn, uploaded)

    def _toggle_upload(self, session_start: str, sess: dict):
        """Toggle upload state for a single session."""
        guild_id = getattr(self, "_guild_active_id", None)
        if not guild_id:
            memberships = getattr(self, "_guild_me", {}).get("memberships", [])
            guild_id = memberships[0]["guild_id"] if memberships else None
        if not guild_id: return
        uploaded = session_start in getattr(self, "_guild_uploaded_starts", set())
        if uploaded:
            def _del():
                try:
                    import urllib.parse
                    self._guild_api("DELETE", f"/guild/{guild_id}/sessions/my/{urllib.parse.quote(session_start, safe='')}",
                                    params={"token": self._guild_session_token})
                    self._guild_uploaded_starts.discard(session_start)
                    # Invalidate members cache
                    if hasattr(self, "_members_cache"): self._members_cache.pop(guild_id, None)
                    self.after(0, self._refresh)
                except Exception as e:
                    print(f"[Upload] Delete failed: {e}")
                    self.after(0, lambda msg=str(e): messagebox.showerror("Error", f"Delete failed: {msg}"))
            threading.Thread(target=_del, daemon=True).start()
        else:
            # Serialize and upload
            ser = dict(sess)
            if hasattr(ser.get("start"), "isoformat"): ser["start"] = ser["start"].isoformat()
            if hasattr(ser.get("end"),   "isoformat"): ser["end"]   = ser["end"].isoformat()
            def _up():
                try:
                    self._guild_api("POST", f"/guild/{guild_id}/sessions/upload",
                                    params={"token": self._guild_session_token},
                                    body={"sessions": [ser]})
                    if not hasattr(self, "_guild_uploaded_starts"):
                        self._guild_uploaded_starts = set()
                    self._guild_uploaded_starts.add(session_start)
                    if hasattr(self, "_members_cache"): self._members_cache.pop(guild_id, None)
                    self.after(0, self._refresh)
                except Exception as e:
                    print(f"[Upload] Upload failed: {e}")
                    self.after(0, lambda msg=str(e): messagebox.showerror("Error", f"Upload failed: {msg}"))
            threading.Thread(target=_up, daemon=True).start()

    def _guild_sync_uploads(self):
        """Sync which sessions are uploaded — call once at startup if in a guild."""
        guild_id = getattr(self, "_guild_active_id", None)
        if not guild_id:
            memberships = getattr(self, "_guild_me", {}).get("memberships", [])
            guild_id = memberships[0]["guild_id"] if memberships else None
        if not self._guild_session_token or not guild_id: return
        def _fetch():
            try:
                data = self._guild_api("GET", f"/guild/{guild_id}/sessions/my-uploads",
                                       params={"token": self._guild_session_token})
                self._guild_uploaded_starts = set(data.get("uploaded", []))
            except Exception as e:
                print(f"[Upload] Sync failed (non-fatal): {e}")
        threading.Thread(target=_fetch, daemon=True).start()

    def _guild_upload_all(self):
        """Upload all current sessions to guild."""
        guild_id = getattr(self, "_guild_active_id", None)
        if not guild_id:
            memberships = getattr(self, "_guild_me", {}).get("memberships", [])
            guild_id = memberships[0]["guild_id"] if memberships else None
        if not guild_id: return
        serialized = []
        for s in self.sessions:
            ser = dict(s)
            if hasattr(ser.get("start"), "isoformat"): ser["start"] = ser["start"].isoformat()
            if hasattr(ser.get("end"),   "isoformat"): ser["end"]   = ser["end"].isoformat()
            serialized.append(ser)
        def _up():
            try:
                # Upload in batches of 50
                for i in range(0, len(serialized), 50):
                    batch = serialized[i:i+50]
                    r = self._guild_api("POST", f"/guild/{guild_id}/sessions/upload",
                                        params={"token": self._guild_session_token},
                                        body={"sessions": batch})
                uploaded = {s.get("start","") for s in serialized if s.get("start")}
                self._guild_uploaded_starts = uploaded
                if hasattr(self, "_members_cache"): self._members_cache.pop(guild_id, None)
                self.after(0, lambda: messagebox.showinfo(
                    "Upload All", f"Uploaded {len(serialized)} sessions to guild."))
                self.after(0, self._refresh)
            except RuntimeError as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: messagebox.showerror("Error", msg))
        threading.Thread(target=_up, daemon=True).start()

    # ── Guild Sessions page ────────────────────────────────────────────────────
    def _guild_show_sessions(self, guild_id: str):
        """Main guild sessions view — all members' sessions newest first."""
        self._guild_content_loading("  📋  Sessions")
        import json as _json
        from datetime import datetime

        def _load():
            try:
                data = self._guild_api("GET", f"/guild/{guild_id}/sessions",
                                       params={"token": self._guild_session_token, "limit": "200"})
                self.after(0, lambda: _render(data))
            except RuntimeError as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: ctk.CTkLabel(
                    self._guild_content, text=f"Error: {msg}",
                    text_color=RED, font=F_BODY).pack(padx=16, pady=8))

        def _render(data):
            for w in self._guild_content.winfo_children(): w.destroy()
            # Header
            hdr = ctk.CTkFrame(self._guild_content, fg_color="transparent")
            hdr.pack(fill="x", padx=16, pady=(10,4))
            ctk.CTkLabel(hdr, text="  📋  Sessions",
                         font=F_HEAD, text_color=GOLD_LT, anchor="w").pack(side="left")
            gold_btn(hdr, "🏆 Top Sessions",
                     lambda: self._guild_show_top(guild_id),
                     w=140, h=32).pack(side="right")
            ctk.CTkFrame(self._guild_content, fg_color=GOLD_DK, height=1).pack(fill="x", padx=16, pady=(0,4))

            sessions = data.get("sessions", [])
            total    = data.get("total", 0)
            ctk.CTkLabel(self._guild_content,
                         text=f"  {total} sessions",
                         font=F_SMALL, text_color=DIM2, anchor="w").pack(fill="x", padx=16)

            scroll = ctk.CTkScrollableFrame(self._guild_content, fg_color="transparent")
            scroll.pack(fill="both", expand=True, padx=8, pady=4)

            # Column headers
            hrow = ctk.CTkFrame(scroll, fg_color=BG3, corner_radius=4)
            hrow.pack(fill="x", pady=(0,2))
            for col, w in [("Player",100),("Character",90),("Type",120),
                           ("Date",90),("Dur",60),("Gold",90),
                           ("Doublons",90),("Rare",70),("Bonus",80),
                           ("Harvest",80),("XP",80),("",40)]:
                ctk.CTkLabel(hrow, text=col, width=w, font=F_SMALL,
                             text_color=GOLD, justify="center").pack(side="left", padx=2)

            is_lo = is_leader_or_officer = False
            memberships = getattr(self, "_guild_me", {}).get("memberships", [])
            for m in memberships:
                if m["guild_id"] == guild_id and m["omt_grade"] in ("leader","officer"):
                    is_lo = True; break

            # Trier par date décroissante (plus récent en haut)
            def _session_dt(s):
                try:
                    return s.get("session_start") or s.get("uploaded_at") or ""
                except Exception:
                    return ""
            sessions_sorted = sorted(sessions, key=_session_dt, reverse=True)

            # Rendu par batch de 30 pour ne pas bloquer l'UI sur 200 sessions
            from datetime import datetime as _dt
            BATCH = 30
            state = {"idx": 0, "current_day": None}

            def _render_batch():
                if not scroll.winfo_exists(): return  # navigation pendant le rendu
                batch_end = min(state["idx"] + BATCH, len(sessions_sorted))
                for i in range(state["idx"], batch_end):
                    s   = sessions_sorted[i]
                    raw = _session_dt(s)
                    try:
                        day = raw[:10]
                        dt_obj = _dt.strptime(day, "%Y-%m-%d")
                        day_label = dt_obj.strftime("%A %d %B %Y").capitalize()
                    except Exception:
                        day = raw[:10] if raw else "Unknown"
                        day_label = day

                    if day != state["current_day"]:
                        state["current_day"] = day
                        sep = ctk.CTkFrame(scroll, fg_color="transparent")
                        sep.pack(fill="x", pady=(8 if i > 0 else 2, 2))
                        ctk.CTkFrame(sep, fg_color=BORDER, height=1).pack(
                            side="left", fill="x", expand=True, padx=(4,8), pady=6)
                        ctk.CTkLabel(sep, text=day_label, font=F_SMALL_B,
                                     text_color=GOLD, anchor="center").pack(side="left")
                        ctk.CTkFrame(sep, fg_color=BORDER, height=1).pack(
                            side="left", fill="x", expand=True, padx=(8,4), pady=6)

                    self._guild_draw_session_row(scroll, s, guild_id, is_lo, i,
                                                  on_click_player=lambda uid=s["user_id"], uname=s["username"]:
                                                  self._guild_show_player_sessions(guild_id, uid, uname))

                state["idx"] = batch_end
                if state["idx"] < len(sessions_sorted):
                    # Planifier le prochain batch sans bloquer l'UI
                    scroll.after(0, _render_batch)

            _render_batch()

        threading.Thread(target=_load, daemon=True).start()

    def _guild_draw_session_row(self, parent, s: dict, guild_id: str,
                                 can_delete: bool, idx: int, on_click_player=None):
        """Draw one session row in the guild sessions view."""
        from datetime import datetime
        data  = s.get("data", {})
        bg    = ROW_A if idx % 2 == 0 else ROW_B
        row   = ctk.CTkFrame(parent, fg_color=bg, corner_radius=3)
        row.pack(fill="x", pady=1)

        # Compute values
        def _gold(d):
            return sum(q for c,items in d.get("loots",{}).items()
                       if c=="Gold & Currency"
                       for n,q in items.items() if "gold" in n.lower())
        def _doub(d):
            return sum(q for c,items in d.get("loots",{}).items()
                       if c=="Gold & Currency"
                       for n,q in items.items() if "doubloon" in n.lower())
        def _rare(d):
            return sum(len(items) for c,items in d.get("loots",{}).items()
                       if c not in ("Gold & Currency","Harvesting"))
        def _harv(d):
            return sum(q for c,items in d.get("loots",{}).items()
                       if c=="Harvesting" for _,q in items.items())
        def _exp(d):  return sum(d.get("aspects_gained",{}).values())
        def _mins(d):
            try:
                s2 = datetime.fromisoformat(d.get("start",""))
                e2 = datetime.fromisoformat(d.get("end",""))
                return max(1, (e2-s2).total_seconds()/60)
            except: return 1

        mins   = _mins(data)
        gold   = _gold(data); doub = _doub(data)
        rare   = _rare(data); harv = _harv(data); exp = _exp(data)
        dt_str = data.get("start","")[:10] if data.get("start") else "—"
        char   = data.get("player","?")
        stype  = data.get("type","—")
        dur    = f"{int(mins)}m"

        def _r(v): return f"{v/max(1,mins)*60:,.0f}/h"

        # Player name — clickable
        player_btn = ctk.CTkButton(row, text=s.get("username","?"),
                                    width=100, height=26, anchor="w",
                                    fg_color="transparent", text_color=GOLD_LT,
                                    hover_color=BG4, font=F_SMALL,
                                    command=on_click_player)
        player_btn.pack(side="left", padx=2)

        for text, w in [
            (char[:12],  90), (stype[:16], 120), (dt_str, 90), (dur, 60),
            (f"{gold:,}\n({_r(gold)})", 90),
            (f"{doub:,}\n({_r(doub)})", 90),
            (f"{rare}", 70), ("—", 80),
            (f"{harv:,}", 80),
            (f"{exp:,.0f}", 80),
        ]:
            ctk.CTkLabel(row, text=text, width=w, font=F_SMALL,
                         text_color=TEXT, justify="center").pack(side="left", padx=2)

        # Delete button for leaders/officers
        if can_delete:
            def _del(sid=s["id"]):
                if not messagebox.askyesno("Delete", "Delete this session?"): return
                def _do():
                    try:
                        self._guild_api("DELETE", f"/guild/{guild_id}/sessions/{sid}",
                                        params={"token": self._guild_session_token})
                        self.after(0, lambda: self._guild_show_sessions(guild_id))
                    except RuntimeError as e:
                        err_msg = str(e)
                        self.after(0, lambda msg=err_msg: messagebox.showerror("Error", msg))
                threading.Thread(target=_do, daemon=True).start()
            ctk.CTkButton(row, text="🗑", width=36, height=26,
                          fg_color="transparent", text_color=RED,
                          hover_color=BG4, font=F_SMALL,
                          command=_del).pack(side="right", padx=2)

    def _guild_show_player_sessions(self, guild_id: str, user_id: str, username: str):
        """Show all sessions for a specific player — with back button."""
        self._guild_content_loading(f"  👤  {username}")

        def _load():
            try:
                data = self._guild_api("GET", f"/guild/{guild_id}/sessions",
                                       params={"token": self._guild_session_token,
                                               "user_id": user_id, "limit": "200"})
                self.after(0, lambda: _render(data))
            except RuntimeError as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: ctk.CTkLabel(
                    self._guild_content, text=f"Error: {msg}",
                    text_color=RED, font=F_BODY).pack(padx=16, pady=8))

        def _render(data):
            for w in self._guild_content.winfo_children(): w.destroy()
            # Back button
            hdr = ctk.CTkFrame(self._guild_content, fg_color="transparent")
            hdr.pack(fill="x", padx=16, pady=(10,4))
            dim_btn(hdr, "← Back", lambda: self._guild_show_sessions(guild_id),
                    w=90, h=30).pack(side="left")
            ctk.CTkLabel(hdr, text=f"  👤  {username}",
                         font=F_HEAD, text_color=GOLD_LT).pack(side="left", padx=12)
            ctk.CTkFrame(self._guild_content, fg_color=GOLD_DK, height=1).pack(fill="x", padx=16, pady=(0,4))

            sessions = data.get("sessions", [])
            ctk.CTkLabel(self._guild_content,
                         text=f"  {len(sessions)} sessions",
                         font=F_SMALL, text_color=DIM2, anchor="w").pack(fill="x", padx=16)

            scroll = ctk.CTkScrollableFrame(self._guild_content, fg_color="transparent")
            scroll.pack(fill="both", expand=True, padx=8, pady=4)

            is_lo = False
            memberships = getattr(self, "_guild_me", {}).get("memberships", [])
            for m in memberships:
                if m["guild_id"] == guild_id and m["omt_grade"] in ("leader","officer"):
                    is_lo = True; break

            for i, s in enumerate(sessions):
                self._guild_draw_session_row(scroll, s, guild_id, is_lo, i,
                                              on_click_player=None)

        threading.Thread(target=_load, daemon=True).start()

    def _guild_show_top(self, guild_id: str):
        """Top Sessions window — Top 10 global + Top 5 per location."""
        win = ctk.CTkToplevel(self)
        win.title("Top Sessions"); win.geometry("820x600")
        win.configure(fg_color=BG); win.grab_set()
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        self._set_win_icon(win)
        ctk.CTkLabel(win, text="🏆  Top Sessions",
                     font=("Georgia",16,"bold"), text_color=GOLD_LT).pack(pady=(14,4))
        ctk.CTkFrame(win, fg_color=GOLD_DK, height=1).pack(fill="x", padx=20, pady=(0,8))
        status = ctk.CTkLabel(win, text="Loading...", text_color=DIM2, font=F_BODY)
        status.pack(pady=4)

        def _load():
            try:
                data = self._guild_api("GET", f"/guild/{guild_id}/sessions/top",
                                       params={"token": self._guild_session_token})
                self.after(0, lambda: _render(data))
            except RuntimeError as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: status.configure(
                    text=f"Error: {msg}", text_color=RED))

        def _draw_top_row(parent, rank: int, s: dict):
            from datetime import datetime
            data  = s.get("data",{})
            score = s.get("score",0)
            row   = ctk.CTkFrame(parent, fg_color=BG2 if rank%2==0 else BG3, corner_radius=4)
            row.pack(fill="x", pady=1, padx=4)
            medal = {1:"🥇",2:"🥈",3:"🥉"}.get(rank, f"#{rank}")
            ctk.CTkLabel(row, text=medal, width=36, font=F_BODY, text_color=GOLD).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=s.get("username","?"), width=110,
                         font=F_SMALL_B, text_color=GOLD_LT, anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=data.get("player","?"), width=90,
                         font=F_SMALL, text_color=TEXT, anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=data.get("location","—"), width=140,
                         font=F_SMALL, text_color=DIM, anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=f"{score:,.0f} gp/h", width=100,
                         font=F_SMALL_B, text_color=GOLD, anchor="e").pack(side="right", padx=8)
            dt_str = (data.get("start","")[:10]) if data.get("start") else "—"
            ctk.CTkLabel(row, text=dt_str, width=90,
                         font=F_SMALL, text_color=DIM2).pack(side="right", padx=4)

        def _render(data):
            status.pack_forget()
            nb = ctk.CTkTabview(win, fg_color=BG2,
                                segmented_button_fg_color=BG3,
                                segmented_button_selected_color=GOLD_DK,
                                segmented_button_selected_hover_color=GOLD,
                                text_color=TEXT)
            nb.pack(fill="both", expand=True, padx=16, pady=4)
            t_global = nb.add("\U0001f30d Global Top 10")
            t_local  = nb.add("\U0001f4cd By Location & Type")

            # Global top 10
            sf_g = ctk.CTkScrollableFrame(t_global, fg_color="transparent")
            sf_g.pack(fill="both", expand=True)
            ctk.CTkLabel(sf_g, text="  Gold + Doublons / hour",
                         font=F_SMALL, text_color=DIM2, anchor="w").pack(fill="x", padx=8, pady=2)
            for i, s in enumerate(data.get("top_global",[]), 1):
                _draw_top_row(sf_g, i, s)

            # By Location & Type
            sf_l = ctk.CTkScrollableFrame(t_local, fg_color="transparent")
            sf_l.pack(fill="both", expand=True)
            cats = data.get("top_by_category", {})

            CAT_ICONS = {
                "Boating":    "\U0001f6a2",
                "Harvesting": "\U0001f33f",
                "Dungeon":    "\u2694",
                "Wilderness": "\U0001f30d",
                "Other":      "\U0001f4cd",
            }

            for cat_name in ["Boating", "Harvesting", "Dungeon", "Wilderness", "Other"]:
                cat_data = cats.get(cat_name)
                if not cat_data: continue
                icon = CAT_ICONS.get(cat_name, "\U0001f4cd")

                # En-tête catégorie
                ctk.CTkLabel(sf_l, text=f"  {icon}  {cat_name}",
                             font=F_HEAD, text_color=GOLD_LT, anchor="w"
                             ).pack(fill="x", padx=8, pady=(12, 2))
                ctk.CTkFrame(sf_l, fg_color=GOLD_DK, height=1
                             ).pack(fill="x", padx=8, pady=(0, 4))

                if isinstance(cat_data, list):
                    # Boating / Harvesting / Other — liste directe
                    for i, s in enumerate(cat_data, 1):
                        _draw_top_row(sf_l, i, s)
                elif isinstance(cat_data, dict):
                    # Dungeon / Wilderness — sous-sections
                    for sub_name, sub_sessions in cat_data.items():
                        ctk.CTkLabel(sf_l, text=f"    \u25b6  {sub_name}",
                                     font=F_BODY_B, text_color=GOLD, anchor="w"
                                     ).pack(fill="x", padx=16, pady=(8, 2))
                        ctk.CTkFrame(sf_l, fg_color=BORDER, height=1
                                     ).pack(fill="x", padx=16, pady=(0, 2))
                        for i, s in enumerate(sub_sessions, 1):
                            _draw_top_row(sf_l, i, s)

        threading.Thread(target=_load, daemon=True).start()

    def _guild_logout(self):
        token = self._guild_session_token
        # Nettoyer l'état local immédiatement (pas besoin d'attendre le réseau)
        self._guild_session_token = None
        self._save_guild_token(None)
        self._guild_render()
        # Invalider le token côté serveur en arrière-plan (non bloquant)
        def _revoke():
            try:
                self._guild_api("POST", "/auth/logout", params={"token": token})
            except Exception as e:
                print(f"[Logout] Token revocation failed (non-fatal): {e}")
        if token:
            threading.Thread(target=_revoke, daemon=True).start()

    def _guild_load_avatar(self, parent, url, size=46):
        if not url: return
        import urllib.request, io
        def _fetch():
            try:
                req = urllib.request.Request(url, headers={"User-Agent":"OMT/1.0"})
                with urllib.request.urlopen(req, timeout=5) as r: data = r.read()
                from PIL import Image as PILImage
                img = PILImage.open(io.BytesIO(data)).convert("RGBA").resize((size,size), PILImage.LANCZOS)
                ph  = ImageTk.PhotoImage(img); self._keep(ph)
                self.after(0, lambda: ctk.CTkLabel(parent, image=ph, text="",
                           fg_color="transparent").pack(side="left", padx=(12,4)))
            except: pass
        threading.Thread(target=_fetch, daemon=True).start()

    def _guild_do_login(self):
        self._guild_status_lbl.configure(text="Connecting to Guild API...")
        def _fetch_url():
            try:
                resp = self._guild_api("GET", "/auth/url")
                url  = resp["url"]
                self.after(0, lambda u=url: _start_oauth(u))
            except RuntimeError as e:
                err = str(e)
                self.after(0, lambda msg=err: [
                    self._guild_status_lbl.configure(text="Connection failed."),
                    messagebox.showerror("Error",
                        f"Cannot reach Guild API.\nMake sure the backend is running.\n\n{msg}")
                ])
        def _start_oauth(url):
            self._guild_status_lbl.configure(text="Waiting for Discord login...")
            threading.Thread(target=self._guild_oauth_server, args=(url,), daemon=True).start()
        threading.Thread(target=_fetch_url, daemon=True).start()

    def _guild_oauth_server(self, oauth_url: str):
        import http.server, urllib.parse, webbrowser, threading
        result = {"code": None, "state": None, "error": None}
        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                print(f"[OAuth] Received: {self.path}")
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)
                if parsed.path not in ("/callback", "/"):
                    self.send_response(204); self.end_headers(); return
                if "code" in params:
                    result["code"]  = params["code"][0]
                    result["state"] = params.get("state", [None])[0]
                    html = b"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{background:#080808;color:#e8dcc8;font-family:'Segoe UI',sans-serif;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
.box{background:#111;border:1px solid #c8952a;border-radius:10px;padding:40px 60px;text-align:center;}
.star{font-size:48px;color:#c8952a;margin-bottom:16px;}
h2{color:#c8952a;margin:0 0 8px;}p{color:#aa9980;margin:0;}</style></head>
<body><div class="box"><div class="star">&#10022;</div>
<h2>Connected!</h2><p>You can close this tab.<br>OMT will update automatically.</p>
</div></body></html>"""
                elif "error" in params:
                    result["error"] = params["error"][0]
                    html = b"<html><body>Authentication failed.</body></html>"
                else:
                    html = b"<html><body>Unexpected.</body></html>"
                self.send_response(200)
                self.send_header("Content-Type","text/html; charset=utf-8")
                self.end_headers(); self.wfile.write(html)
                threading.Thread(target=self.server.shutdown, daemon=True).start()
        port = 8766
        try: server = http.server.HTTPServer(("127.0.0.1", port), CallbackHandler)
        except OSError:
            port = 8767; server = http.server.HTTPServer(("127.0.0.1", port), CallbackHandler)
        webbrowser.open(oauth_url)
        server.serve_forever()
        if result["code"]:
            self._guild_exchange_code(result["code"], result["state"])
        else:
            err = result.get("error","Unknown error")
            self.after(0, lambda msg=err: self._guild_status_lbl.configure(text=f"Login failed: {msg}"))

    def _guild_exchange_code(self, code: str, state: str):
        import os, threading, json as _json, urllib.request
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        try:
            from requests_oauthlib import OAuth2Session
        except ImportError:
            self.after(0, lambda: self._guild_status_lbl.configure(text="Missing: pip install requests-oauthlib"))
            return
        CLIENT_ID="1513359601054126140"; CLIENT_SECRET="1IqsjewYel8P8sL_UMdLURAoCmf6R3k8"
        TOKEN_URL="https://discord.com/api/oauth2/token"
        REDIRECT_URI="http://127.0.0.1:8766/callback"
        def _do():
            try:
                callback_url = f"{REDIRECT_URI}?code={code}&state={state or ''}"
                discord = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, state=state,
                                        scope=["identify","guilds"])
                token = discord.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET,
                                             authorization_response=callback_url)
                access_token = token.get("access_token")
                if not access_token: raise RuntimeError("No access_token")
                print("[OAuth] Exchange OK")
            except Exception as exc:
                err_msg = str(exc)
                print(f"[OAuth] Exchange error: {err_msg}")
                self.after(0, lambda msg=err_msg: self._guild_status_lbl.configure(
                    text=f"Discord auth failed: {msg}")); return
            try:
                body = _json.dumps({"access_token":access_token,
                                     "refresh_token":token.get("refresh_token",""),
                                     "state":state or ""}).encode()
                req = urllib.request.Request(self.GUILD_API+"/auth/register", data=body,
                    headers={"Content-Type":"application/json","User-Agent":"OMT/1.0"}, method="POST")
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = _json.loads(r.read())
                session_token = data.get("session_token")
                if session_token:
                    self._guild_session_token = session_token
                    self._save_guild_token(session_token)
                    self.after(0, lambda: self._show("Guild"))
                else:
                    self.after(0, lambda: self._guild_status_lbl.configure(text="Login failed — no session token."))
            except Exception as exc:
                err_msg = str(exc)
                self.after(0, lambda msg=err_msg: self._guild_status_lbl.configure(text=f"Backend error: {msg}"))
        threading.Thread(target=_do, daemon=True).start()

    def _guild_create_flow(self):
        win = ctk.CTkToplevel(self); win.title("Create Guild"); win.geometry("480x500")
        win.configure(fg_color=BG); win.grab_set()
        win.protocol("WM_DELETE_WINDOW", win.destroy); self._set_win_icon(win)
        ctk.CTkLabel(win, text="Create a Guild", font=("Georgia",16,"bold"),
                     text_color=GOLD_LT).pack(pady=(16,4))
        ctk.CTkLabel(win, text="Select the Discord server for your guild.",
                     font=F_BODY, text_color=DIM).pack(pady=(0,10))
        ctk.CTkFrame(win, fg_color=GOLD_DK, height=1).pack(fill="x", padx=20, pady=(0,8))
        status = ctk.CTkLabel(win, text="Loading your Discord servers...", text_color=DIM2, font=F_SMALL)
        status.pack(pady=4)
        scroll_f = ctk.CTkScrollableFrame(win, fg_color=BG2, height=340)
        scroll_f.pack(fill="both", expand=True, padx=16, pady=4)
        def _load():
            try:
                data = self._guild_api("GET", "/guild/discord-servers",
                                       params={"token":self._guild_session_token})
                servers = data.get("admin_servers",[])
                self.after(0, lambda: _render(servers))
            except RuntimeError as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: status.configure(text=f"Error: {msg}", text_color=RED))
        def _render(servers):
            status.pack_forget()
            for w in scroll_f.winfo_children(): w.destroy()
            if not servers:
                ctk.CTkLabel(scroll_f, text="No admin servers found.", text_color=DIM2, font=F_BODY).pack(pady=20)
                return
            for s in servers:
                row = ctk.CTkFrame(scroll_f, fg_color=BG3, corner_radius=4)
                row.pack(fill="x", pady=3, padx=4)
                ctk.CTkLabel(row, text=s["name"], font=F_BODY, text_color=TEXT, anchor="w").pack(side="left", padx=12, pady=8)
                if s.get("has_guild"):
                    ctk.CTkLabel(row, text="Already exists", text_color=DIM2, font=F_SMALL).pack(side="right", padx=8)
                    def _join_leader(sv=s):
                        def _do():
                            try:
                                self._guild_api("POST", f"/guild/{sv['id']}/join-as-leader",
                                                params={"token":self._guild_session_token})
                                self.after(0, lambda: [win.destroy(), self._show("Guild"), self._guild_render()])
                            except RuntimeError as e:
                                err_msg = str(e)
                                self.after(0, lambda msg=err_msg: messagebox.showerror("Error", msg))
                        threading.Thread(target=_do, daemon=True).start()
                    dim_btn(row, "Join as Leader", _join_leader, w=120, h=30).pack(side="right", padx=4, pady=4)
                else:
                    def _create(sv=s):
                        def _do():
                            try:
                                self._guild_api("POST", "/guild/create",
                                    params={"token":self._guild_session_token},
                                    body={"discord_server_id":sv["id"],"discord_server_name":sv["name"],"discord_icon":sv.get("icon")})
                                self.after(0, lambda: [win.destroy(), self._show("Guild"), self._guild_render()])
                            except RuntimeError as e:
                                err_msg = str(e)
                                self.after(0, lambda msg=err_msg: messagebox.showerror("Error", msg))
                        threading.Thread(target=_do, daemon=True).start()
                    gold_btn(row, "Create", _create, w=80, h=30).pack(side="right", padx=8, pady=4)
        threading.Thread(target=_load, daemon=True).start()

    def _guild_join_flow(self):
        win = ctk.CTkToplevel(self); win.title("Join a Guild"); win.geometry("480x460")
        win.configure(fg_color=BG); win.grab_set()
        win.protocol("WM_DELETE_WINDOW", win.destroy); self._set_win_icon(win)
        ctk.CTkLabel(win, text="Join a Guild", font=("Georgia",16,"bold"), text_color=GOLD_LT).pack(pady=(16,4))
        ctk.CTkLabel(win, text="Your grade is detected automatically from your Discord roles.",
                     font=F_BODY, text_color=DIM).pack(pady=(0,10))
        ctk.CTkFrame(win, fg_color=GOLD_DK, height=1).pack(fill="x", padx=20, pady=(0,8))
        status = ctk.CTkLabel(win, text="Loading guilds...", text_color=DIM2, font=F_SMALL); status.pack(pady=4)
        scroll_f = ctk.CTkScrollableFrame(win, fg_color=BG2, height=320)
        scroll_f.pack(fill="both", expand=True, padx=16, pady=4)
        def _load():
            try:
                data = self._guild_api("GET", "/guild/discord-servers",
                                       params={"token":self._guild_session_token})
                self.after(0, lambda: _render(data.get("joinable_servers",[])))
            except RuntimeError as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: status.configure(text=f"Error: {msg}", text_color=RED))
        def _render(servers):
            status.pack_forget()
            for w in scroll_f.winfo_children(): w.destroy()
            if not servers:
                ctk.CTkLabel(scroll_f, text="No guilds available.", text_color=DIM2, font=F_BODY).pack(pady=20)
                return
            for s in servers:
                row = ctk.CTkFrame(scroll_f, fg_color=BG3, corner_radius=4)
                row.pack(fill="x", pady=3, padx=4)
                ctk.CTkLabel(row, text=s["name"], font=F_BODY, text_color=TEXT, anchor="w").pack(side="left", padx=12, pady=8)
                def _join(sv=s):
                    def _do():
                        try:
                            res = self._guild_api("POST", f"/guild/{sv['id']}/join",
                                                  params={"token":self._guild_session_token})
                            grade = res.get("omt_grade","member")
                            self.after(0, lambda: [win.destroy(),
                                messagebox.showinfo("Joined!", f"You joined {sv['name']} as {grade}."),
                                self._guild_render()])
                        except RuntimeError as e:
                            err_msg = str(e)
                            self.after(0, lambda msg=err_msg: messagebox.showerror("Error", msg))
                    threading.Thread(target=_do, daemon=True).start()
                gold_btn(row, "Join", _join, w=80, h=30).pack(side="right", padx=8, pady=4)
        threading.Thread(target=_load, daemon=True).start()

    def _set_win_icon(self, win):
        """Apply OMT icon to CTkToplevel — must use after(250) to override CTk default icon."""
        ico_path = str(ASSETS_DIR / "O-MTSmall.ico")
        def _apply():
            if not win.winfo_exists(): return
            try:
                # Tell CTk not to override our icon
                win._iconbitmap_method_called = True
                win.iconbitmap(ico_path)
            except:
                try:
                    if hasattr(self, "_main_icon_ph"):
                        win.iconphoto(True, self._main_icon_ph)
                except: pass
        win.after(250, _apply)
        # Restaurer l icone principale quand ce toplevel se ferme
        def _on_destroy(e=None):
            if hasattr(self, "_reapply_main_icon"):
                self.after(150, self._reapply_main_icon)
        win.bind("<Destroy>", _on_destroy)



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

        # Pro Tips
        p_tips = gold_panel("Pro Tips", "💡")
        bul(p_tips, [
            "Add your survival script at the end of the START script using sysmsg",
            "Add your resupply script at the end of the END script",
        ])
        ctk.CTkFrame(p_tips, height=6, fg_color="transparent").pack()

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
