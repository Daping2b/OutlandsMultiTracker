#!/usr/bin/env python3
"""
OMT — check_methods.py
Valide l'intégrité de main.py avant toute livraison.

Usage :
    python check_methods.py              # vérifie main.py dans le dossier courant
    python check_methods.py path/main.py # chemin explicite

Checks effectués :
  1. py_compile — pas d'erreur de syntaxe
  2. Checklist des méthodes guild obligatoires (0 absent, 0 doublon)
  3. Doublons de méthodes dans la même classe
  4. Appels HTTP synchrones sur le main thread (sans threading)
  5. Lambdas avec variable de boucle non capturée
  6. connect_args check_same_thread (PostgreSQL interdit)
  7. Présence du port dev 59876 hors bloc commentaire

Retourne 0 si tout est OK, 1 si au moins un problème.
"""

import sys
import re
import ast
import py_compile
import tempfile
import os
from collections import Counter

# ── Couleurs terminal ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✅ {msg}{RESET}")
def err(msg):  print(f"  {RED}❌ {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠️  {msg}{RESET}")
def info(msg): print(f"  {CYAN}ℹ️  {msg}{RESET}")

# ── Checklist des méthodes guild ───────────────────────────────────────────────
# Source de vérité : état réel du main.py v0.72.1 (vérifié le 2026-07-09)
# Méthodes de classe App (def dans la classe)
GUILD_METHODS_CLASS = [
    "_guild_do_login",
    "_guild_oauth_server",
    "_guild_exchange_code",
    "_guild_render",
    "_guild_state_login",
    "_guild_state_profile",
    "_guild_state_guild",
    "_guild_content_loading",
    "_guild_show_admin",
    "_guild_show_bot",
    "_guild_show_members",
    "_guild_show_profile",
    "_guild_show_characters",
    
    "_guild_create_flow",
    "_guild_join_flow",
    "_guild_load_avatar",
    "_guild_logout",
    "_superadmin_panel",
    "_set_win_icon",
    "_guild_member_characters",
    "_guild_member_presentiel",
    "_guild_show_sessions",
    "_guild_draw_session_row",
    "_guild_show_player_sessions",
    "_guild_show_top",
    "_guild_sync_uploads",
    "_guild_upload_all",
    "_toggle_upload",
    "_draw_upload_cell",
    "_on_upload_all_toggle",
    "_upload_selected_to_guild",
    "_get_bonus_for_session",
    "_get_current_bonuses",
    "_fetch_bonuses",
    "_guild_api",
    "_build_guild",
    "_load_guild_token",
    "_save_guild_token",
]

# Fonction module-level (pas dans une classe)
GUILD_FUNCTIONS_MODULE = [
    "_expand_abbrev",
]

# ── Helpers ────────────────────────────────────────────────────────────────────
def load_source(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def get_non_comment_lines(src):
    """Retourne les lignes sans les commentaires inline ni les lignes # pures."""
    result = []
    for line in src.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            result.append("")
        else:
            # Supprimer la partie commentaire inline
            result.append(re.sub(r'#.*$', '', line))
    return result

def class_method_map(src):
    """
    Retourne un dict {class_name: [(method_name, lineno), ...]}
    et une liste des fonctions module-level [(func_name, lineno)].
    """
    lines = src.splitlines()
    current_class = None
    classes = {}
    module_funcs = []

    for i, line in enumerate(lines, 1):
        cm = re.match(r'^class (\w+)', line)
        if cm:
            current_class = cm.group(1)

        dm = re.match(r'(    def |def )(\w+)\s*\(', line)
        if dm:
            indent = dm.group(1)
            name   = dm.group(2)
            if indent == "def ":          # module-level
                module_funcs.append((name, i))
                current_class = None      # reset (rare mais possible)
            else:                          # méthode de classe
                classes.setdefault(current_class, []).append((name, i))

    return classes, module_funcs

# ── Checks ─────────────────────────────────────────────────────────────────────

def check_syntax(path):
    print(f"\n{BOLD}[1/7] Syntaxe Python (py_compile){RESET}")
    try:
        py_compile.compile(path, doraise=True)
        ok("Aucune erreur de syntaxe")
        return True
    except py_compile.PyCompileError as e:
        err(f"Erreur de syntaxe : {e}")
        return False

def check_guild_methods(src, classes, module_funcs):
    print(f"\n{BOLD}[2/7] Checklist méthodes guild{RESET}")
    failures = 0

    # Chercher dans TOUS les fichiers .py du projet (Mixins inclus)
    all_class_methods = {}   # name -> [(file, class, lineno)]
    all_module_funcs  = {}   # name -> (file, lineno)

    py_files = [f for f in os.listdir(".") if f.endswith(".py")]
    for pyfile in py_files:
        try:
            with open(pyfile, "r", encoding="utf-8") as f:
                fsrc = f.read()
            fclasses, fmodule = class_method_map(fsrc)
            for cls, methods in fclasses.items():
                for name, lineno in methods:
                    all_class_methods.setdefault(name, []).append((pyfile, cls, lineno))
            for name, lineno in fmodule:
                all_module_funcs.setdefault(name, []).append((pyfile, lineno))
        except Exception:
            pass

    # Méthodes de classe attendues
    for m in GUILD_METHODS_CLASS:
        entries = all_class_methods.get(m, [])
        if not entries:
            err(f"ABSENT  : {m}")
            failures += 1
        elif len(entries) > 1:
            # Doublon seulement si dans le MÊME fichier
            by_file = {}
            for pyfile, cls, lineno in entries:
                by_file.setdefault(pyfile, []).append((cls, lineno))
            real_dupes = {f: e for f, e in by_file.items() if len(e) > 1}
            if real_dupes:
                err(f"DOUBLON : {m} — " +
                    ", ".join(f"{f}:{c}:L{l}" for f, pairs in real_dupes.items() for c, l in pairs))
                failures += 1
            else:
                pyfile, cls, lineno = entries[0]
                ok(f"{m:<40}  {pyfile}:{cls}:L{lineno}")
        else:
            pyfile, cls, lineno = entries[0]
            ok(f"{m:<40}  {pyfile}:{cls}:L{lineno}")

    # Fonctions module-level attendues
    for f in GUILD_FUNCTIONS_MODULE:
        entries = all_module_funcs.get(f, [])
        if not entries:
            err(f"ABSENT (module-level) : {f}")
            failures += 1
        else:
            pyfile, lineno = entries[0]
            ok(f"{f:<40}  {pyfile}:module:L{lineno}")

    if failures == 0:
        ok(f"Toutes les méthodes guild présentes ({len(GUILD_METHODS_CLASS) + len(GUILD_FUNCTIONS_MODULE)} / {len(GUILD_METHODS_CLASS) + len(GUILD_FUNCTIONS_MODULE)})")
    return failures == 0

def check_duplicates(classes):
    print(f"\n{BOLD}[3/7] Doublons de méthodes dans la même classe{RESET}")
    failures = 0
    for cls, methods in classes.items():
        names = [n for n, _ in methods]
        dupes = {n: [l for nm, l in methods if nm == n]
                 for n, c in Counter(names).items() if c > 1}
        for name, lines in dupes.items():
            err(f"Doublon dans {cls}: def {name} → lignes {lines}")
            failures += 1
    if failures == 0:
        ok("Aucun doublon dans aucune classe")
    return failures == 0

def check_sync_http(src):
    print(f"\n{BOLD}[4/7] Appels HTTP synchrones sur le main thread{RESET}")
    # Patterns suspects : urllib.request.urlopen / requests.get|post hors thread
    clean_lines = get_non_comment_lines(src)
    failures = 0
    http_pattern = re.compile(
        r'(urllib\.request\.(urlopen|Request)|requests\.(get|post|put|delete|patch))\s*\('
    )
    thread_wrap  = re.compile(r'threading\.Thread|daemon=True')

    # Simplification : signaler les appels HTTP dont la ligne ne contient pas "target="
    # et qui ne sont pas dans une définition de fonction dédiée au réseau
    for i, line in enumerate(clean_lines, 1):
        if http_pattern.search(line):
            # Vérifier le contexte : chercher threading dans les 5 lignes autour
            context = "\n".join(clean_lines[max(0, i-6):i+2])
            if not thread_wrap.search(context):
                warn(f"L{i}: possible appel HTTP synchrone → {line.strip()[:80]}")
                failures += 1

    if failures == 0:
        ok("Aucun appel HTTP synchrone détecté hors thread")
    else:
        warn(f"{failures} occurrence(s) à vérifier manuellement")
    return True  # warning seulement, pas bloquant

def check_lambda_closure(src):
    print(f"\n{BOLD}[5/7] Lambdas avec variable de boucle non capturée{RESET}")
    clean_lines = get_non_comment_lines(src)
    failures = 0
    # Pattern : lambda: func(var) où var est la variable d'une boucle for/list comp précédente
    # Heuristique : lambda sans paramètre par défaut utilisant une variable simple
    bad_lambda = re.compile(r'lambda\s*:\s*\w+\s*\(\s*\w+\s*\)')
    for_loop   = re.compile(r'\bfor\s+(\w+)\s+in\b')

    for i, line in enumerate(clean_lines, 1):
        if bad_lambda.search(line) and for_loop.search(line):
            err(f"L{i}: lambda potentiellement mal capturée → {line.strip()[:80]}")
            failures += 1

    if failures == 0:
        ok("Aucune lambda mal capturée détectée")
    return failures == 0

def check_same_thread(src):
    print(f"\n{BOLD}[6/7] connect_args check_same_thread (PostgreSQL interdit){RESET}")
    if "check_same_thread" in src:
        lines = src.splitlines()
        for i, l in enumerate(lines, 1):
            if "check_same_thread" in l:
                err(f"L{i}: check_same_thread détecté (SQLite seulement) → {l.strip()}")
        return False
    ok("Aucune occurrence de check_same_thread")
    return True

def check_dev_port(src):
    print(f"\n{BOLD}[7/7] Port dev 59876 hors commentaire{RESET}")
    clean_lines = get_non_comment_lines(src)
    failures = 0
    for i, line in enumerate(clean_lines, 1):
        if "59876" in line:
            err(f"L{i}: port dev 59876 présent dans le code → {line.strip()[:80]}")
            failures += 1
    if failures == 0:
        ok("Port dev 59876 absent du code (OK pour la prod)")
    return failures == 0

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "main.py"

    if not os.path.exists(path):
        print(f"{RED}Fichier introuvable : {path}{RESET}")
        sys.exit(1)

    print(f"\n{BOLD}{CYAN}{'='*56}{RESET}")
    print(f"{BOLD}{CYAN}  OMT — check_methods.py{RESET}")
    print(f"{BOLD}{CYAN}  Fichier : {path}  ({os.path.getsize(path)//1024} KB){RESET}")
    print(f"{BOLD}{CYAN}{'='*56}{RESET}")

    src     = load_source(path)
    classes, module_funcs = class_method_map(src)

    results = []
    results.append(check_syntax(path))
    results.append(check_guild_methods(src, classes, module_funcs))
    results.append(check_duplicates(classes))
    check_sync_http(src)       # warning only
    results.append(check_lambda_closure(src))
    results.append(check_same_thread(src))
    results.append(check_dev_port(src))

    # ── Résumé ────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*56}{RESET}")
    passed = sum(results)
    total  = len(results)
    if passed == total:
        print(f"{BOLD}{GREEN}  ✅  TOUT OK ({passed}/{total}) — main.py prêt à livrer{RESET}")
        print(f"{BOLD}{'='*56}{RESET}\n")
        sys.exit(0)
    else:
        print(f"{BOLD}{RED}  ❌  {total - passed} CHECK(S) EN ÉCHEC ({passed}/{total} OK){RESET}")
        print(f"{BOLD}{RED}  Corriger avant de livrer.{RESET}")
        print(f"{BOLD}{'='*56}{RESET}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()