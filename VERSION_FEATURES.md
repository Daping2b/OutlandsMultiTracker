# OMT — Version Features Reference
> Ce fichier est mis à jour à chaque nouvelle version.
> Avant toute modification de `main.py`, vérifier que TOUTES ces features sont présentes.

## Version courante : 0.62.3

---

## Checklist obligatoire — main.py

| Feature | Introduite en | Signature à vérifier |
|---------|--------------|----------------------|
| Guild tab + _build_guild | 0.52 | `"Guild"` dans `tab_defs` + `def _build_guild` |
| BONUS_SYMBOLS dict | 0.59 | `BONUS_SYMBOLS = {` |
| Fetch via API GitHub (pas raw CDN) | 0.60.1 | `api.github.com` dans `_fetch_bonuses` |
| base64 decode du contenu API | 0.60.1 | `base64.b64decode` dans `_fetch_bonuses` |
| os._exit(0) dans _prompt_update | 0.60 | `os._exit(0)` dans `run()` |
| Fallback semaine précédente bonus | 0.59.7 | `max(self.bonuses_db.keys())` dans `_get_current_bonuses` |
| Symbole bonus à la fin du nom | 0.59.10 | `f"   {base}  {symbol}"` dans `_fill_act_tree` |
| Sanctuary/Challenger toujours affichés | 0.59.9 | `is_type_indicator` dans `_fill_act_tree` |
| Tooltip bonus sur hover tree | 0.59.4 | `_tree_tooltip_show` + `_tree_tooltip_hide` |
| fid=fpath.name (pas chemin absolu) | 0.61 | `fid=fpath.name` dans `parse_logs` |
| sessions_before pour known_ids | 0.62.1 | `sessions_before=len(sessions)` dans `parse_logs` |
| Skip fichiers vides (0 bytes) | 0.62.2 | `st_size == 0` dans `parse_logs` |
| should_skip_item (potions/outils) | 0.62 | `def should_skip_item` + `_SKIP_KEYWORDS` |
| Gold/doubloons depuis dépôts bancaires | 0.61 | `gold into your bank` dans parser |
| XP multi-mots aspects | 0.61 | `([\w ]+?) Aspect` dans regex XP |
| Delete 3 boutons modal custom | 0.62 | `result[0]=="session"` + `result[0]=="permanent"` |
| Extraction zip anticipée (pre-extract) | 0.62 | `pre_extract_dir` + `--pre-extracted` dans `do_update` |
| DETACHED_PROCESS simple | 0.62.3 | `creationflags=subprocess.DETACHED_PROCESS,` (sans CREATE_NEW_PROCESS_GROUP) |
| Migration known_files (chemins absolus) | 0.61 | `os.sep in f` dans `_load_logs` |
| Ossuary Lv-4 coordonnées | 0.60.2 | Dans `Dungeon.json` — polygon non `[0,0]` |
| save_json avec gestion erreur | 0.59 | `try/except` dans `def save_json` |
| _refresh_bonus_tree sans except:pass | 0.59 | `def _refresh_bonus_tree` sans `except: pass` |
| _tree_building guard | 0.59 | `_tree_building` dans `_fill_act_tree` |
| version_newer supporte X.Y.Z | 0.57 | `maxlen = max(len(r), len(l))` dans `version_newer` |

---

## Checklist obligatoire — updater.py

| Feature | Introduite en | Signature à vérifier |
|---------|--------------|----------------------|
| Polling 50ms (pas 1s) | 0.62.3 | `time.sleep(0.05)` |
| Timeout 3s (60 iterations) | 0.62.3 | `range(60)` |
| os.replace() atomique | 0.62.3 | `os.replace(` |
| Relaunch avant cleanup | 0.62.3 | `Popen(` avant `def cleanup` |
| Cleanup en thread background | 0.62.3 | `threading.Thread(target=cleanup` |
| Support --pre-extracted | 0.62 | `--pre-extracted` dans argv parsing |
| Pas de shutil.copy2 | 0.62.3 | `shutil.copy2` absent |
| Pas de time.sleep(1) | 0.62.3 | `time.sleep(1)` absent |
| Pas de time.sleep(0.5) avant relaunch | 0.60 | `time.sleep(0.5)` absent avant `Popen` |

---

## Procédure avant toute modification

1. Vérifier que le `main.py` uploadé contient TOUTES les signatures ci-dessus
2. Si une feature manque → l'appliquer en premier avant la nouvelle modification
3. Après génération → re-vérifier la checklist complète
4. Mettre à jour ce fichier avec les nouvelles features de la version générée

---

## Historique des versions majeures

| Version | Date | Highlights |
|---------|------|------------|
| 0.62.3 | 2026-05-31 | Updater v4 optimisé, relaunch immédiat |
| 0.62.2 | 2026-05-31 | Skip fichiers vides, fix known_ids critique |
| 0.62.1 | 2026-05-31 | Fix sessions_before (bug sessions manquantes) |
| 0.62 | 2026-05-31 | Delete 3 boutons, filtrage items, pre-extract |
| 0.61 | 2026-05-31 | Fix parse_logs, gold banque, XP multi-mots |
| 0.60.2 | 2026-05-30 | Ossuary Lv-4, consolidation tous les fixes |
| 0.60.1 | 2026-05-30 | Fetch bonus via API GitHub |
| 0.60 | 2026-05-30 | os._exit, updater v4 polling 50ms |
| 0.59 | 2026-05-30 | Stability pass, Activities tree refonte |
| 0.58 | 2026-05-30 | Bonus icons tree, garbage collection fix |
| 0.57 | 2026-05-30 | version_newer X.Y.Z, update SSL fix complet |
| 0.55 | 2026-05-30 | Patch Notes fix affichage catégories |
| 0.54 | 2026-05-30 | SSL fix auto-update |
| 0.53 | 2026-05-30 | Fetch bonus automatique au démarrage |
| 0.52 | 2026-05-30 | Guild nav, bonus icons tree, Patch Notes redesign |
