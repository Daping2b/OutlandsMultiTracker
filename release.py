#!/usr/bin/env python3
"""
OMT — release.py
Automatise le processus de release complet.

Usage :
    python release.py 0.75           # release git + SCP uniquement
    python release.py 0.75 --full    # release COMPLÈTE : git + build + zip + upload
    python release.py 0.75 --dry     # simulation sans rien écrire ni pusher
    python release.py 0.75 --upload  # upload du zip existant sur GitHub uniquement

Étapes --full (10 au total) :
  1-7. Vérifications + bump version + git + SCP (identiques au mode standard)
  8.   Build PyInstaller via build.bat (sortie streamée en temps réel)
  9.   Zip du dist/ en Python natif (plus rapide que Compress-Archive)
  10.  Upload zip sur la release GitHub via API
"""

import sys
import os
import re
import json
import zipfile
import subprocess
import argparse
from datetime import date
from pathlib import Path

# ── Chargement automatique du .env local ──────────────────────────────────────
_ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# ── Couleurs terminal ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):       print(f"  {GREEN}✅ {msg}{RESET}")
def err(msg):      print(f"  {RED}❌ {msg}{RESET}")
def warn(msg):     print(f"  {YELLOW}⚠️  {msg}{RESET}")
def info(msg):     print(f"  {CYAN}ℹ️  {msg}{RESET}")
def step(n, msg):  print(f"\n{BOLD}[{n}] {msg}{RESET}")
def die(msg):
    print(f"\n{BOLD}{RED}ABORT : {msg}{RESET}\n")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────
VPS_USER    = "ubuntu"
VPS_HOST    = "37.187.219.83"
VPS_CL_PATH = "~/omt-website/changelog.json"
SSH_KEY     = os.path.join(os.path.expanduser("~"), ".ssh", "omt_deploy")

GITHUB_OWNER = "Daping2b"
GITHUB_REPO  = "OutlandsMultiTracker"
GITHUB_TOKEN = os.environ.get("OMT_GITHUB_TOKEN", "")
ZIP_FILE     = "OutlandsMultiTracker.zip"
DIST_DIR     = os.path.join("dist", "OutlandsMultiTracker")

OMT_API_URL       = os.environ.get("OMT_API_URL",       "https://outlands-multi-tracker.com:8765")
OMT_RELEASE_KEY   = os.environ.get("OMT_RELEASE_KEY",   "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OMT_LOGO_URL      = "https://www.outlands-multi-tracker.com/assets/O-MTSmall.png"
OMT_SITE_URL      = "https://www.outlands-multi-tracker.com"

VERSION_FILE   = os.path.join("config", "version.json")
CHANGELOG_FILE = os.path.join("config", "changelog.json")
DEV_OVERRIDE   = os.path.join("config", "dev_override.json")
SETTINGS_FILE  = os.path.join("config", "settings.json")
MAIN_PY        = "main.py"
CHECK_SCRIPT   = "check_methods.py"

# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_version(v):
    parts = v.split(".")
    if len(parts) not in (2, 3):
        raise ValueError(f"Format invalide : {v!r} (attendu X.YY ou X.YY.Z)")
    return tuple(int(p) for p in parts)

def version_gt(new, old):
    def pad(t, n): return t + (0,) * (n - len(t))
    l = max(len(new), len(old))
    return pad(new, l) > pad(old, l)

def run(cmd, dry=False, capture=False):
    display = cmd if isinstance(cmd, str) else " ".join(cmd)
    if dry:
        info(f"[DRY] {display}")
        return 0, ""
    result = subprocess.run(
        cmd, shell=isinstance(cmd, str),
        capture_output=capture, text=True
    )
    return result.returncode, result.stdout.strip() if capture else ""

def run_streamed(cmd, dry=False):
    """Lance une commande et streame sa sortie en temps réel."""
    if dry:
        info(f"[DRY] {cmd}")
        return 0
    proc = subprocess.Popen(
        cmd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )
    for line in proc.stdout:
        print(f"  {line}", end="")
    proc.wait()
    return proc.returncode

def scp_upload(local, remote, dry=False):
    cmd = ["scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
           "-o", "BatchMode=yes", local, f"{VPS_USER}@{VPS_HOST}:{remote}"]
    display = f"scp -i ~/.ssh/omt_deploy {local} {VPS_USER}@{VPS_HOST}:{remote}"
    if dry:
        info(f"[DRY] {display}")
        return True
    info(f"Envoi : {display}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        ok(f"Upload OK → {remote}")
        return True
    else:
        err(f"Échec SCP (code {result.returncode})")
        if result.stderr:
            err(f"  {result.stderr.strip()}")
        return False

# ── Étapes ────────────────────────────────────────────────────────────────────

def check_version_format(new_ver_str, total):
    step(f"1/{total}", "Format et cohérence de la version")
    try:
        new_ver = parse_version(new_ver_str)
    except ValueError as e:
        die(str(e))
    if not os.path.exists(VERSION_FILE):
        die(f"{VERSION_FILE} introuvable")
    with open(VERSION_FILE, encoding="utf-8") as f:
        current = json.load(f)
    current_str = current.get("version", "0.0")
    try:
        current_ver = parse_version(current_str)
    except ValueError:
        current_ver = (0, 0)
    ok(f"Version actuelle : {current_str}")
    if not version_gt(new_ver, current_ver):
        die(f"La nouvelle version {new_ver_str} n'est pas supérieure à {current_str}")
    ok(f"Nouvelle version  : {new_ver_str}  ({'patch' if len(new_ver) == 3 else 'majeure'})")


def check_main_py(dry, total):
    step(f"2/{total}", "Intégrité main.py (check_methods.py)")
    if not os.path.exists(CHECK_SCRIPT):
        warn(f"{CHECK_SCRIPT} introuvable — vérification ignorée")
        return
    rc, _ = run([sys.executable, CHECK_SCRIPT], dry=dry)
    if rc != 0 and not dry:
        die("check_methods.py a détecté des problèmes. Corriger avant de releaser.")
    ok("check_methods.py OK")


def check_changelog(new_ver_str, dry, total):
    step(f"3/{total}", f"changelog.json contient la version {new_ver_str}")
    if not os.path.exists(CHANGELOG_FILE):
        die(f"{CHANGELOG_FILE} introuvable")
    with open(CHANGELOG_FILE, encoding="utf-8") as f:
        changelog = json.load(f)
    versions = [e.get("version") for e in changelog]
    if new_ver_str not in versions:
        die(
            f"Version {new_ver_str} absente de {CHANGELOG_FILE}.\n"
            f"    Ajoute l'entrée changelog avant de releaser.\n"
            f"    Versions présentes : {versions[:5]}..."
        )
    entry = next(e for e in changelog if e.get("version") == new_ver_str)
    changes = entry.get("changes", [])
    ok(f"Version trouvée dans le changelog ({len(changes)} entrées)")
    today = date.today().isoformat()
    if entry.get("date") != today:
        warn(f"La date dans changelog.json est {entry.get('date')!r}, aujourd'hui c'est {today!r}")
    superadmin_entries = [c for c in changes if "superadmin" in c.get("text", "").lower()]
    if superadmin_entries:
        err(f"{len(superadmin_entries)} entrée(s) SuperAdmin à supprimer du changelog :")
        for c in superadmin_entries:
            err(f"  - {c['text'][:80]}")
        die("Supprimer les entrées SuperAdmin avant de releaser.")
    ok("Aucune entrée SuperAdmin dans le changelog")


def check_security_files(dry, total):
    step(f"4/{total}", "Fichiers dangereux absents / propres")
    if os.path.exists(DEV_OVERRIDE):
        die(f"{DEV_OVERRIDE} présent ! Supprimer avant de releaser (mode staging actif).")
    ok(f"{DEV_OVERRIDE} absent ✓")
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                settings = {}
        token = settings.get("guild_token") or settings.get("session_token") or ""
        if token:
            warn(f"{SETTINGS_FILE} contient un token ({token[:8]}...) — exclu du build par build.bat")
        else:
            ok(f"{SETTINGS_FILE} sans token ✓")
    else:
        ok(f"{SETTINGS_FILE} absent ✓")
    if os.path.exists(MAIN_PY):
        with open(MAIN_PY, encoding="utf-8") as f:
            src = f.read()
        lines = [l for l in src.splitlines() if "59876" in l and not l.lstrip().startswith("#")]
        if lines:
            die(f"Port dev 59876 présent dans {MAIN_PY} :\n" +
                "\n".join(f"    {l.strip()}" for l in lines))
        ok("Port dev 59876 absent de main.py ✓")


def bump_version(new_ver_str, dry, total):
    step(f"5/{total}", f"Bump version.json → {new_ver_str}")
    if dry:
        info("[DRY] version.json resterait inchangé")
        return
    with open(VERSION_FILE, encoding="utf-8") as f:
        data = json.load(f)
    data["version"] = new_ver_str
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    ok(f"version.json mis à jour : {new_ver_str}")


def git_commit_tag_push(new_ver_str, dry, total):
    step(f"6/{total}", "git add + commit + tag + push")
    rc, _ = run("git rev-parse --git-dir", dry=False, capture=True)
    if rc != 0:
        die("Pas dans un repo git")
    tag = f"v{new_ver_str}"
    commit_msg = f"{tag} — OMT release"
    rc, existing = run(f"git tag -l {tag}", dry=False, capture=True)
    if existing.strip() == tag:
        die(f"Le tag {tag} existe déjà.")
    info("Synchronisation avec origin/main...")
    run("git stash", dry=dry)
    rc, _ = run("git pull origin main --rebase", dry=dry)
    if rc != 0 and not dry:
        warn("git pull --rebase a échoué — fetch + reset...")
        run("git rebase --abort", dry=dry)
        run("git fetch origin", dry=dry)
        rc2, _ = run("git reset --hard origin/main", dry=dry)
        if rc2 != 0 and not dry:
            die("Impossible de synchroniser avec origin/main.")
    run("git stash pop", dry=dry)
    ok("Synchronisé avec origin/main")
    for cmd in [
        f'git add config/version.json config/changelog.json {MAIN_PY}',
        f'git commit -m "{commit_msg}"',
        f'git tag {tag}',
        f'git push origin main',
        f'git push origin {tag}',
    ]:
        rc, _ = run(cmd, dry=dry)
        if rc != 0 and not dry:
            die(f"Échec : {cmd}")
        ok(f"{'[DRY] ' if dry else ''}{cmd}")


def do_scp(dry, total):
    step(f"7/{total}", "Upload changelog.json → VPS")
    if not dry and not os.path.exists(SSH_KEY):
        err(f"Clé SSH introuvable : {SSH_KEY}")
        warn(f"Lance manuellement : scp {CHANGELOG_FILE} {VPS_USER}@{VPS_HOST}:{VPS_CL_PATH}")
        return
    scp_upload(CHANGELOG_FILE, VPS_CL_PATH, dry)


def do_build(dry, total):
    step(f"8/{total}", "Build PyInstaller (build.bat)")
    if dry:
        info("[DRY] build.bat serait lancé ici")
        return
    if not os.path.exists("build.bat"):
        die("build.bat introuvable")
    info("Lancement de build.bat — sortie en temps réel :")
    print()
    rc = run_streamed("build.bat")
    print()
    if rc != 0:
        die(f"build.bat a échoué (code {rc})")
    if not os.path.isdir(DIST_DIR):
        die(f"Dossier dist introuvable après build : {DIST_DIR}")
    ok(f"Build terminé → {DIST_DIR}/")


def do_zip(dry, total):
    step(f"9/{total}", f"Création du zip → {ZIP_FILE}")
    if dry:
        info(f"[DRY] {DIST_DIR}/ → {ZIP_FILE}")
        return
    dist_path = Path(DIST_DIR)
    if not dist_path.exists():
        die(f"{DIST_DIR} introuvable — le build a-t-il réussi ?")
    if os.path.exists(ZIP_FILE):
        os.remove(ZIP_FILE)
    file_count = 0
    with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file in dist_path.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(dist_path.parent)
                zf.write(file, arcname)
                file_count += 1
    size_mb = os.path.getsize(ZIP_FILE) / 1024 / 1024
    ok(f"{ZIP_FILE} créé — {file_count} fichiers, {size_mb:.1f} MB")


def do_github_upload(new_ver_str, dry, total):
    import urllib.request, urllib.error
    step(f"10/{total}", f"Upload {ZIP_FILE} → GitHub Release v{new_ver_str}")
    if not GITHUB_TOKEN:
        die("OMT_GITHUB_TOKEN non défini. Lance : $env:OMT_GITHUB_TOKEN = '...'")
    tag = f"v{new_ver_str}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "OMT-release-script/1.0",
    }
    if dry:
        info(f"[DRY] Upload {ZIP_FILE} sur la release {tag}")
        return
    # Récupérer ou créer la release
    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tags/{tag}"
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            release = json.loads(r.read())
        ok("Release GitHub trouvée")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            warn(f"Release {tag} absente — création...")
            create_body = json.dumps({
                "tag_name": tag, "name": f"OMT {tag}",
                "body": f"Outlands Multi Tracker {tag}",
                "draft": False, "prerelease": False,
            }).encode()
            create_req = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases",
                data=create_body,
                headers={**headers, "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(create_req, timeout=15) as r:
                release = json.loads(r.read())
            ok(f"Release {tag} créée")
        else:
            die(f"Erreur GitHub API : {e.code} {e.reason}")
    # Supprimer l'asset existant si déjà uploadé
    upload_url = release["upload_url"].replace("{?name,label}", "")
    for asset in release.get("assets", []):
        if asset["name"] == ZIP_FILE:
            warn("Asset existant — suppression...")
            del_req = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/assets/{asset['id']}",
                headers=headers, method="DELETE"
            )
            try:
                urllib.request.urlopen(del_req, timeout=10)
                ok("Asset existant supprimé")
            except Exception as e:
                warn(f"Suppression échouée (non bloquant) : {e}")
    # Upload
    info(f"Upload en cours ({os.path.getsize(ZIP_FILE)/1024/1024:.1f} MB)...")
    with open(ZIP_FILE, "rb") as f:
        zip_data = f.read()
    upload_req = urllib.request.Request(
        f"{upload_url}?name={ZIP_FILE}", data=zip_data,
        headers={**headers, "Content-Type": "application/zip",
                 "Content-Length": str(len(zip_data))},
        method="POST"
    )
    try:
        with urllib.request.urlopen(upload_req, timeout=180) as r:
            result = json.loads(r.read())
        ok(f"Upload réussi : {result.get('browser_download_url', '?')}")
        ok(f"Release : https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tag/{tag}")
    except urllib.error.HTTPError as e:
        die(f"Erreur upload : {e.code} — {e.read().decode(errors='replace')[:200]}")


def do_broadcast_patchnote(new_ver_str, dry, total):
    import urllib.request, urllib.error
    step_n = total  # dernière étape
    step(f"{step_n}/{total}", f"Broadcast patchnote v{new_ver_str} → Official Notice channels")

    if dry:
        info("[DRY] Broadcast patchnote ignoré en mode dry")
        return

    if not OMT_RELEASE_KEY:
        warn("OMT_RELEASE_KEY non défini — broadcast ignoré")
        warn("Ajoute OMT_RELEASE_KEY dans OMT_WIN\\.env")
        return

    # ── Lire le changelog ──────────────────────────────────────────────────────
    with open(CHANGELOG_FILE, encoding="utf-8") as f:
        changelog = json.load(f)
    entry = next((e for e in changelog if e.get("version") == new_ver_str), None)
    if not entry:
        warn(f"Version {new_ver_str} non trouvée dans changelog — broadcast ignoré")
        return

    changes = [c for c in entry.get("changes", [])
               if "superadmin" not in c.get("text", "").lower()]

    # ── Générer le titre via Claude ────────────────────────────────────────────
    title = _generate_title(new_ver_str, changes)
    ok(f"Titre généré : {title!r}")

    # ── Mapper les types → émojis ──────────────────────────────────────────────
    TYPE_EMOJI = {
        "NEW FEATURE": ("✨", "New Features"),
        "BUG FIX":     ("🐛", "Bug Fixes"),
        "IMPROVEMENT": ("⚡", "Improvements"),
        "SECURITY":    ("🔒", "Security"),
        "NEW ZONE":    ("🗺", "New Zones"),
        "CHANGE":      ("🔧", "Changes"),
    }

    # Regrouper par type en conservant l'ordre d'apparition
    groups = {}
    for c in changes:
        t = c.get("type", "CHANGE").upper()
        if t not in groups:
            groups[t] = []
        groups[t].append(c["text"])

    # ── Construire les fields Discord ─────────────────────────────────────────
    fields = []
    for type_key, texts in groups.items():
        emoji, label = TYPE_EMOJI.get(type_key, ("•", type_key.title()))
        value = "\n".join(f"› {t}" for t in texts)
        # Discord : max 1024 chars par field value
        if len(value) > 1024:
            value = value[:1020] + "..."
        fields.append({"name": f"{emoji}  {label}", "value": value, "inline": False})

    # Séparateur + bouton téléchargement
    fields.append({
        "name": "\u200b",
        "value": f"[📥 Download]({OMT_SITE_URL})  •  [🌐 Website]({OMT_SITE_URL})",
        "inline": False
    })

    # ── Construire l'embed ────────────────────────────────────────────────────
    embed = {
        "author": {
            "name": "Outlands Multi Tracker",
            "icon_url": OMT_LOGO_URL,
            "url": OMT_SITE_URL,
        },
        "title": f"OMT v{new_ver_str} — {title}",
        "url": OMT_SITE_URL,
        "color": 0xC8952A,  # doré OMT
        "fields": fields,
        "thumbnail": {"url": OMT_LOGO_URL},
        "footer": {
            "text": "OMT Bot",
            "icon_url": OMT_LOGO_URL,
        },
        "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }

    # ── Appel API ─────────────────────────────────────────────────────────────
    info("Envoi du broadcast embed...")
    body = json.dumps({"embed": embed}).encode()
    req = urllib.request.Request(
        f"{OMT_API_URL}/admin/broadcast-embed",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Release-Key": OMT_RELEASE_KEY,
            "User-Agent": "OMT-release-script/1.0",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
        sent = result.get("sent", "?")
        ok(f"Broadcast envoyé sur {sent} canal(aux)")
    except urllib.error.HTTPError as e:
        warn(f"Broadcast échoué ({e.code}) — release non bloquée")
        warn(f"  {e.read().decode(errors='replace')[:120]}")
    except Exception as e:
        warn(f"Broadcast échoué ({e}) — release non bloquée")


def _generate_title(ver: str, changes: list) -> str:
    """Génère un titre court via Claude API. Fallback sur titre générique si échec."""
    if not ANTHROPIC_API_KEY:
        return _fallback_title(changes)
    try:
        import urllib.request
        summary = "\n".join(
            f"- [{c.get('type','?')}] {c.get('text','')}" for c in changes[:15]
        )
        prompt = (
            f"Voici les changements de la version {ver} d'OMT (Outlands Multi Tracker), "
            f"un tracker de sessions pour le jeu Ultima Online:\n\n{summary}\n\n"
            "Génère un titre ultra-court (2-4 mots MAX, en anglais) qui résume le thème principal "
            "de cette release. Style exemples: 'Performance Update', 'Guild Overhaul', 'Bot Revamp', "
            "'Quality of Life'. Réponds UNIQUEMENT avec le titre, rien d'autre."
        )
        body = json.dumps({
            "model": "claude-sonnet-4-6",
            "max_tokens": 20,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "User-Agent": "OMT-release-script/1.0",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
        title = resp["content"][0]["text"].strip().strip('"').strip("'")
        # Sanity check — pas plus de 6 mots
        if len(title.split()) > 6:
            return _fallback_title(changes)
        return title
    except Exception as e:
        warn(f"Génération titre échouée ({e}) — titre générique utilisé")
        return _fallback_title(changes)


def _fallback_title(changes: list) -> str:
    """Titre de fallback basé sur la catégorie dominante."""
    from collections import Counter
    types = [c.get("type", "").upper() for c in changes]
    counts = Counter(types)
    dominant = counts.most_common(1)[0][0] if counts else ""
    fallback_map = {
        "NEW FEATURE": "New Features",
        "BUG FIX":     "Bug Fixes",
        "IMPROVEMENT": "Improvements",
        "SECURITY":    "Security Update",
        "NEW ZONE":    "New Zones",
        "CHANGE":      "Update",
    }
    return fallback_map.get(dominant, "Update")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OMT release script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemples :\n"
            "  python release.py 0.75           # release git + SCP\n"
            "  python release.py 0.75 --full    # release COMPLÈTE (build + zip + upload)\n"
            "  python release.py 0.75 --dry     # simulation\n"
            "  python release.py 0.75 --upload  # upload zip existant seulement"
        )
    )
    parser.add_argument("version", help="Numéro de version cible (ex: 0.75 ou 0.75.1)")
    parser.add_argument("--dry",          action="store_true", help="Simulation sans modification")
    parser.add_argument("--full",         action="store_true", help="Release complète : git + build + zip + upload")
    parser.add_argument("--upload",       action="store_true", help="Upload du zip existant sur GitHub uniquement")
    parser.add_argument("--no-broadcast", action="store_true", help="Ne pas envoyer le broadcast patchnote")
    args = parser.parse_args()

    new_ver_str = args.version.strip()
    dry         = args.dry

    # ── Mode --upload seul ────────────────────────────────────────────────────
    if args.upload and not args.full:
        print(f"\n{BOLD}{CYAN}{'='*56}{RESET}")
        print(f"{BOLD}{CYAN}  OMT — release.py --upload  {'[DRY RUN]' if dry else ''}{RESET}")
        print(f"{BOLD}{CYAN}  Cible : v{new_ver_str}{RESET}")
        print(f"{BOLD}{CYAN}{'='*56}{RESET}")
        if not os.path.exists(ZIP_FILE):
            die(f"{ZIP_FILE} introuvable.")
        do_github_upload(new_ver_str, dry, 1)
        print(f"\n{BOLD}{'='*56}{RESET}\n")
        return

    # ── Mode standard ou --full ───────────────────────────────────────────────
    total = 11 if args.full else 8
    mode_label = "FULL" if args.full else "standard"

    print(f"\n{BOLD}{CYAN}{'='*56}{RESET}")
    print(f"{BOLD}{CYAN}  OMT — release.py [{mode_label}]  {'[DRY RUN]' if dry else ''}{RESET}")
    print(f"{BOLD}{CYAN}  Cible : v{new_ver_str}{RESET}")
    print(f"{BOLD}{CYAN}{'='*56}{RESET}")

    check_version_format(new_ver_str, total)
    check_main_py(dry, total)
    check_changelog(new_ver_str, dry, total)
    check_security_files(dry, total)
    bump_version(new_ver_str, dry, total)
    git_commit_tag_push(new_ver_str, dry, total)
    do_scp(dry, total)
    do_broadcast_patchnote(new_ver_str, dry, total) if not args.no_broadcast else warn("Broadcast ignoré (--no-broadcast)")

    if args.full:
        do_build(dry, total)
        do_zip(dry, total)
        do_github_upload(new_ver_str, dry, total)
        print(f"\n{BOLD}{CYAN}{'='*56}{RESET}")
        print(f"{BOLD}{GREEN}  ✅ Release v{new_ver_str} complète !{RESET}")
        print(f"{BOLD}{CYAN}{'='*56}{RESET}\n")
    else:
        print(f"""
  {BOLD}Étapes manuelles restantes :{RESET}

  {CYAN}1.{RESET} {BOLD}.\\build.bat{RESET}
  {CYAN}2.{RESET} Zipper : {BOLD}Compress-Archive -Path "dist\\OutlandsMultiTracker\\*" -DestinationPath "OutlandsMultiTracker.zip" -Force{RESET}
  {CYAN}3.{RESET} Upload : {BOLD}python release.py {new_ver_str} --upload{RESET}

  Ou tout en une fois la prochaine fois :
  {CYAN}→{RESET}  {BOLD}python release.py {new_ver_str} --full{RESET}
        """)

    print(f"\n{BOLD}{'='*56}{RESET}\n")


if __name__ == "__main__":
    main()