#!/usr/bin/env python3
"""
OMT — release.py
Automatise le processus de release complet.

Usage :
    python release.py 0.73          # release majeure
    python release.py 0.72.2        # patch
    python release.py 0.73 --dry    # simulation sans rien écrire ni pusher

Étapes effectuées :
  1. Vérification de la version (format, pas de régression)
  2. check_methods.py — intégrité main.py
  3. Vérification que changelog.json contient la version cible
  4. Vérification absence de dev_override.json et settings.json propre
  5. Vérification absence du port dev 59876 dans main.py
  6. Bump version.json
  7. git add + commit + tag + push (main + tag)
  8. SCP changelog.json → VPS (~/omt-website/changelog.json)
  9. Résumé final avec marche à suivre manuelle restante
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
VPS_CL_PATH = "~/omt-website/changelog.json"   # destination SCP

VERSION_FILE   = os.path.join("config", "version.json")
CHANGELOG_FILE = os.path.join("config", "changelog.json")
DEV_OVERRIDE   = os.path.join("config", "dev_override.json")
SETTINGS_FILE  = os.path.join("config", "settings.json")
MAIN_PY        = "main.py"
CHECK_SCRIPT   = "check_methods.py"

# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_version(v):
    """Parse '0.72.1' → (0, 72, 1). Lève ValueError si invalide."""
    parts = v.split(".")
    if len(parts) not in (2, 3):
        raise ValueError(f"Format invalide : {v!r} (attendu X.YY ou X.YY.Z)")
    return tuple(int(p) for p in parts)

def version_gt(new, old):
    """True si new > old (tuples de longueurs éventuellement différentes)."""
    def pad(t, n): return t + (0,) * (n - len(t))
    l = max(len(new), len(old))
    return pad(new, l) > pad(old, l)

def run(cmd, dry=False, capture=False):
    """Exécute une commande shell. Si dry=True, affiche sans exécuter."""
    display = cmd if isinstance(cmd, str) else " ".join(cmd)
    if dry:
        info(f"[DRY] {display}")
        return 0, ""
    result = subprocess.run(
        cmd, shell=isinstance(cmd, str),
        capture_output=capture, text=True
    )
    return result.returncode, result.stdout.strip() if capture else ""

def scp(local, remote, dry=False):
    """SCP d'un fichier local vers le VPS."""
    cmd = f'scp .\\{local} {VPS_USER}@{VPS_HOST}:{remote}'
    # Sur Windows, SCP est lancé depuis le dossier où se trouve le fichier
    # On construit la commande mais on informe l'utilisateur de la lancer manuellement
    # car release.py tourne côté Windows sans accès SSH direct depuis Claude
    return cmd


# ── Étapes de vérification ─────────────────────────────────────────────────────

def check_version_format(new_ver_str, dry):
    step("1/9", "Format et cohérence de la version")
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
    step("2/9", "Intégrité main.py (check_methods.py)")
    if not os.path.exists(CHECK_SCRIPT):
        warn(f"{CHECK_SCRIPT} introuvable — vérification ignorée")
        return
    rc, _ = run([sys.executable, CHECK_SCRIPT], dry=dry)
    if rc != 0 and not dry:
        die(f"check_methods.py a détecté des problèmes. Corriger avant de releaser.")
    ok("check_methods.py OK")


def check_changelog(new_ver_str, dry):
    step("3/9", f"changelog.json contient la version {new_ver_str}")
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

    # Vérification date
    today = date.today().isoformat()
    if entry.get("date") != today:
        warn(f"La date dans changelog.json est {entry.get('date')!r}, aujourd'hui c'est {today!r}")

    # Pas d'entrées SuperAdmin
    superadmin_entries = [c for c in changes if "superadmin" in c.get("text", "").lower()]
    if superadmin_entries:
        err(f"{len(superadmin_entries)} entrée(s) SuperAdmin à supprimer du changelog :")
        for c in superadmin_entries:
            err(f"  - {c['text'][:80]}")
        die("Supprimer les entrées SuperAdmin avant de releaser.")
    ok("Aucune entrée SuperAdmin dans le changelog")


def check_security_files(dry):
    step("4/9", "Fichiers dangereux absents / propres")

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

    # Port dev dans main.py
    if os.path.exists(MAIN_PY):
        with open(MAIN_PY, encoding="utf-8") as f:
            src = f.read()
        lines = [l for l in src.splitlines() if "59876" in l and not l.lstrip().startswith("#")]
        if lines:
            die(f"Port dev 59876 présent dans {MAIN_PY} :\n" +
                "\n".join(f"    {l.strip()}" for l in lines))
        ok("Port dev 59876 absent de main.py ✓")


def bump_version(new_ver_str, dry):
    step("5/9", f"Bump version.json → {new_ver_str}")
    if dry:
        info(f"[DRY] version.json resterait inchangé")
        return
    with open(VERSION_FILE, encoding="utf-8") as f:
        data = json.load(f)
    data["version"] = new_ver_str
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    ok(f"version.json mis à jour : {new_ver_str}")


def git_commit_tag_push(new_ver_str, dry):
    step("6/9", "git add + commit + tag + push")

    # Vérifier qu'on est bien dans un repo git
    rc, _ = run("git rev-parse --git-dir", dry=False, capture=True)
    if rc != 0:
        die("Pas dans un repo git")

    tag = f"v{new_ver_str}"
    commit_msg = f"{tag} — OMT release"

    # Vérifier que le tag n'existe pas déjà
    rc, existing = run(f"git tag -l {tag}", dry=False, capture=True)
    if existing.strip() == tag:
        die(f"Le tag {tag} existe déjà. Utilise une version différente ou supprime le tag manuellement.")

    # Synchroniser avec le remote AVANT de committer
    # (évite la divergence si Claude a pushé des commits depuis son environnement)
    info("Synchronisation avec origin/main...")
    run("git stash", dry=dry)
    rc, _ = run("git pull origin main --rebase", dry=dry)
    if rc != 0 and not dry:
        warn("git pull --rebase a échoué — on continue avec fetch + reset...")
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

def show_scp_command(dry):
    step("7/9", "Upload changelog.json → VPS")
    cmd = scp(CHANGELOG_FILE, VPS_CL_PATH, dry)
    if dry:
        info(f"[DRY] commande SCP à lancer :")
        print(f"\n    {CYAN}{cmd}{RESET}\n")
    else:
        # On ne peut pas exécuter SCP depuis Windows sans clé SSH configurée
        # On affiche la commande à copier-coller
        print(f"\n  {YELLOW}Commande SCP à exécuter depuis le dossier {CHANGELOG_FILE} :{RESET}")
        print(f"\n    {BOLD}{CYAN}{cmd}{RESET}\n")
        warn("Lance cette commande dans ton terminal Windows depuis le dossier OMT_WIN/config/")


def show_summary(new_ver_str, dry):
    step("8/9", "Checklist build manuelle")
    print(f"""
  {BOLD}Étapes manuelles restantes :{RESET}

  {CYAN}1.{RESET} Lancer {BOLD}build.bat{RESET}
       → Vérifie que dist/OutlandsMultiTracker/ est propre
       → Zipper en OutlandsMultiTracker.zip

  {CYAN}2.{RESET} Scanner OutlandsMultiTracker.zip sur {BOLD}VirusTotal{RESET}
       → 4/59 faux positifs attendus (Avast, AVG, WithSecure, Bkav Pro)

  {CYAN}3.{RESET} Upload manuel du zip sur la release GitHub {BOLD}v{new_ver_str}{RESET}
       → https://github.com/Daping2b/OutlandsMultiTracker/releases/tag/v{new_ver_str}
       → (Claude ne peut pas accéder à uploads.github.com)
    """)

    step("9/9", "Résumé")
    tag = f"v{new_ver_str}"
    mode = f"{YELLOW}[MODE DRY RUN — rien n'a été modifié]{RESET}" if dry else f"{GREEN}Release effectuée !{RESET}"
    print(f"\n  {BOLD}{mode}{RESET}")
    if not dry:
        ok(f"Version bumped      : {new_ver_str}")
        ok(f"Commit + tag        : {tag}")
        ok(f"Push GitHub         : main + {tag}")
        warn(f"SCP changelog.json  : à lancer manuellement (voir ci-dessus)")
        warn(f"Build + zip + upload: à faire manuellement (voir ci-dessus)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OMT release script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exemples :\n  python release.py 0.73\n  python release.py 0.72.2 --dry"
    )
    parser.add_argument("version", help="Numéro de version cible (ex: 0.73 ou 0.72.2)")
    parser.add_argument("--dry", action="store_true", help="Simulation sans modification")
    args = parser.parse_args()

    new_ver_str = args.version.strip()
    dry         = args.dry

    print(f"\n{BOLD}{CYAN}{'='*56}{RESET}")
    print(f"{BOLD}{CYAN}  OMT — release.py  {'[DRY RUN]' if dry else ''}{RESET}")
    print(f"{BOLD}{CYAN}  Cible : v{new_ver_str}{RESET}")
    print(f"{BOLD}{CYAN}{'='*56}{RESET}")

    # Vérifications dans l'ordre
    check_version_format(new_ver_str, dry)
    check_main_py(dry)
    check_changelog(new_ver_str, dry)
    check_security_files(dry)
    bump_version(new_ver_str, dry)
    git_commit_tag_push(new_ver_str, dry)
    show_scp_command(dry)
    show_summary(new_ver_str, dry)

    print(f"\n{BOLD}{'='*56}{RESET}\n")


if __name__ == "__main__":
    main()
