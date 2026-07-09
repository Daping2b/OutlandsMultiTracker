#!/usr/bin/env python3
"""
OMT — release.py
Automatise le processus de release complet.

Usage :
    python release.py 0.73              # release complète
    python release.py 0.72.2            # patch
    python release.py 0.73 --dry        # simulation sans rien écrire ni pusher
    python release.py 0.73 --upload     # upload du zip sur la release GitHub

Étapes release standard :
  1. Vérification de la version (format, pas de régression)
  2. check_methods.py — intégrité main.py
  3. Vérification que changelog.json contient la version cible
  4. Vérification absence de dev_override.json et settings.json propre
  5. Bump version.json
  6. git stash + pull --rebase + stash pop + commit + tag + push
  7. SCP changelog.json → VPS
  8. Résumé final

Étape --upload (séparée, après build.bat + zip) :
  Upload OutlandsMultiTracker.zip sur la release GitHub via API
"""

import sys
import os
import re
import json
import subprocess
import argparse
from datetime import date

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

GITHUB_OWNER   = "Daping2b"
GITHUB_REPO    = "OutlandsMultiTracker"
GITHUB_TOKEN   = os.environ.get("OMT_GITHUB_TOKEN", "")
ZIP_FILE       = "OutlandsMultiTracker.zip"

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

# ── Étapes de vérification ─────────────────────────────────────────────────────

def check_version_format(new_ver_str, dry):
    step("1/8", "Format et cohérence de la version")
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
    return current_str, current_ver


def check_main_py(dry):
    step("2/8", "Intégrité main.py (check_methods.py)")
    if not os.path.exists(CHECK_SCRIPT):
        warn(f"{CHECK_SCRIPT} introuvable — vérification ignorée")
        return
    rc, _ = run([sys.executable, CHECK_SCRIPT], dry=dry)
    if rc != 0 and not dry:
        die("check_methods.py a détecté des problèmes. Corriger avant de releaser.")
    ok("check_methods.py OK")


def check_changelog(new_ver_str, dry):
    step("3/8", f"changelog.json contient la version {new_ver_str}")
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


def check_security_files(dry):
    step("4/8", "Fichiers dangereux absents / propres")

    if os.path.exists(DEV_OVERRIDE):
        die(f"{DEV_OVERRIDE} présent ! Supprimer avant de releaser (mode staging actif).")
    ok(f"{DEV_OVERRIDE} absent ✓")

    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                warn(f"{SETTINGS_FILE} invalide ou vide — OK pour le build")
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


def bump_version(new_ver_str, dry):
    step("5/8", f"Bump version.json → {new_ver_str}")
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


def git_commit_tag_push(new_ver_str, dry):
    step("6/8", "git add + commit + tag + push")

    rc, _ = run("git rev-parse --git-dir", dry=False, capture=True)
    if rc != 0:
        die("Pas dans un repo git")

    tag = f"v{new_ver_str}"
    commit_msg = f"{tag} — OMT release"

    rc, existing = run(f"git tag -l {tag}", dry=False, capture=True)
    if existing.strip() == tag:
        die(f"Le tag {tag} existe déjà. Utilise une version différente ou supprime le tag manuellement.")

    # Synchroniser avec le remote AVANT de committer
    # (évite la divergence si Claude a pushé des commits depuis son environnement)
    info("Synchronisation avec origin/main...")
    run("git stash", dry=dry)
    rc, _ = run("git pull origin main --rebase", dry=dry)
    if rc != 0 and not dry:
        warn("git pull --rebase a échoué — fetch + reset...")
        run("git rebase --abort", dry=dry)
        run("git fetch origin", dry=dry)
        rc2, _ = run("git reset --hard origin/main", dry=dry)
        if rc2 != 0 and not dry:
            die("Impossible de synchroniser avec origin/main. Résous le conflit git manuellement.")
    run("git stash pop", dry=dry)
    ok("Synchronisé avec origin/main")

    cmds = [
        f'git add config/version.json config/changelog.json {MAIN_PY}',
        f'git commit -m "{commit_msg}"',
        f'git tag {tag}',
        f'git push origin main',
        f'git push origin {tag}',
    ]

    for cmd in cmds:
        rc, _ = run(cmd, dry=dry)
        if rc != 0 and not dry:
            die(f"Échec : {cmd}")
        ok(f"{'[DRY] ' if dry else ''}{cmd}")


def do_scp(dry):
    step("7/8", "Upload changelog.json → VPS")
    if not dry and not os.path.exists(SSH_KEY):
        err(f"Clé SSH introuvable : {SSH_KEY}")
        warn(f"Lance manuellement : scp {CHANGELOG_FILE} {VPS_USER}@{VPS_HOST}:{VPS_CL_PATH}")
        return
    scp_upload(CHANGELOG_FILE, VPS_CL_PATH, dry)


def show_summary(new_ver_str, dry):
    step("8/8", "Résumé")
    tag = f"v{new_ver_str}"
    mode = f"{YELLOW}[MODE DRY RUN — rien n'a été modifié]{RESET}" if dry else f"{GREEN}Release effectuée !{RESET}"
    print(f"\n  {BOLD}{mode}{RESET}")
    if not dry:
        ok(f"Version bumped      : {new_ver_str}")
        ok(f"Commit + tag        : {tag}")
        ok(f"Push GitHub         : main + {tag}")
        ok(f"SCP changelog.json  : uploadé sur le VPS")
    print(f"""
  {BOLD}Étapes manuelles restantes :{RESET}

  {CYAN}1.{RESET} {BOLD}.\\build.bat{RESET}
  {CYAN}2.{RESET} Zipper : {BOLD}Compress-Archive -Path "dist\\OutlandsMultiTracker\\*" -DestinationPath "OutlandsMultiTracker.zip" -Force{RESET}
  {CYAN}3.{RESET} Upload : {BOLD}python release.py {new_ver_str} --upload{RESET}
    """)


# ── Upload GitHub Release ──────────────────────────────────────────────────────

def github_upload(new_ver_str, dry):
    """Upload OutlandsMultiTracker.zip sur la release GitHub v{new_ver_str}."""
    import urllib.request
    import urllib.error

    print(f"\n{BOLD}{CYAN}{'='*56}{RESET}")
    print(f"{BOLD}{CYAN}  OMT — release.py --upload  {'[DRY RUN]' if dry else ''}{RESET}")
    print(f"{BOLD}{CYAN}  Cible : v{new_ver_str}{RESET}")
    print(f"{BOLD}{CYAN}{'='*56}{RESET}")

    step("1/3", f"Vérification du zip {ZIP_FILE}")
    if not os.path.exists(ZIP_FILE):
        die(f"{ZIP_FILE} introuvable. Lance d'abord build.bat puis Compress-Archive.")
    size_mb = os.path.getsize(ZIP_FILE) / 1024 / 1024
    ok(f"{ZIP_FILE} trouvé ({size_mb:.1f} MB)")

    step("2/3", f"Récupération de la release v{new_ver_str} sur GitHub")
    tag = f"v{new_ver_str}"
    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tags/{tag}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "OMT-release-script/1.0",
    }

    if dry:
        info(f"[DRY] GET {api_url}")
        info(f"[DRY] Upload {ZIP_FILE} sur la release {tag}")
        ok("Simulation OK")
        return

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            release = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            die(f"Release {tag} introuvable sur GitHub. Lance d'abord : python release.py {new_ver_str}")
        die(f"Erreur GitHub API : {e.code} {e.reason}")
    except Exception as e:
        die(f"Erreur réseau : {e}")

    release_id = release["id"]
    upload_url = release["upload_url"].replace("{?name,label}", "")
    ok(f"Release trouvée : {release.get('name', tag)} (id={release_id})")

    # Supprimer l'asset existant si déjà uploadé
    assets = release.get("assets", [])
    for asset in assets:
        if asset["name"] == ZIP_FILE:
            warn(f"Asset {ZIP_FILE} déjà présent — suppression...")
            del_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/assets/{asset['id']}"
            del_req = urllib.request.Request(del_url, headers=headers, method="DELETE")
            try:
                urllib.request.urlopen(del_req, timeout=10)
                ok("Asset existant supprimé")
            except Exception as e:
                warn(f"Suppression échouée (non bloquant) : {e}")

    step("3/3", f"Upload {ZIP_FILE} → GitHub Release {tag}")
    upload_endpoint = f"{upload_url}?name={ZIP_FILE}"
    with open(ZIP_FILE, "rb") as f:
        zip_data = f.read()

    upload_headers = {
        **headers,
        "Content-Type": "application/zip",
        "Content-Length": str(len(zip_data)),
    }
    upload_req = urllib.request.Request(
        upload_endpoint, data=zip_data,
        headers=upload_headers, method="POST"
    )
    try:
        with urllib.request.urlopen(upload_req, timeout=120) as r:
            result = json.loads(r.read())
        ok(f"Upload réussi : {result.get('browser_download_url', '?')}")
        ok(f"Release : https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tag/{tag}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        die(f"Erreur upload : {e.code} — {body[:200]}")
    except Exception as e:
        die(f"Erreur upload : {e}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OMT release script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemples :\n"
            "  python release.py 0.73            # release complète\n"
            "  python release.py 0.72.2 --dry    # simulation\n"
            "  python release.py 0.73 --upload   # upload zip après build"
        )
    )
    parser.add_argument("version", help="Numéro de version cible (ex: 0.73 ou 0.72.2)")
    parser.add_argument("--dry",    action="store_true", help="Simulation sans modification")
    parser.add_argument("--upload", action="store_true", help="Upload du zip sur la release GitHub")
    args = parser.parse_args()

    new_ver_str = args.version.strip()
    dry         = args.dry

    # Mode upload uniquement
    if args.upload:
        github_upload(new_ver_str, dry)
        print(f"\n{BOLD}{'='*56}{RESET}\n")
        return

    # Release standard
    print(f"\n{BOLD}{CYAN}{'='*56}{RESET}")
    print(f"{BOLD}{CYAN}  OMT — release.py  {'[DRY RUN]' if dry else ''}{RESET}")
    print(f"{BOLD}{CYAN}  Cible : v{new_ver_str}{RESET}")
    print(f"{BOLD}{CYAN}{'='*56}{RESET}")

    check_version_format(new_ver_str, dry)
    check_main_py(dry)
    check_changelog(new_ver_str, dry)
    check_security_files(dry)
    bump_version(new_ver_str, dry)
    git_commit_tag_push(new_ver_str, dry)
    do_scp(dry)
    show_summary(new_ver_str, dry)

    print(f"\n{BOLD}{'='*56}{RESET}\n")


if __name__ == "__main__":
    main()
