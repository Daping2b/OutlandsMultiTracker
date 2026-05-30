# Outlands Multi Tracker v0.1
**by Daping**

---

## Compiler le .exe (une seule fois)

1. Installe **Python 3.11+** depuis https://www.python.org/downloads/
   ⚠️ Coche **"Add Python to PATH"** pendant l'installation

2. Double-clique sur **`build.bat`**
   → Il installe tout et génère le .exe automatiquement

3. Ton application portable se trouve dans :
   ```
   dist\OutlandsMultiTracker\OutlandsMultiTracker.exe
   ```
   Copie le dossier `OutlandsMultiTracker` n'importe où — il est 100% portable.

---

## Structure du projet

```
OMT_WIN/
├── main.py                  ← Code source
├── OMT.spec                 ← Config PyInstaller
├── requirements.txt         ← Dépendances
├── build.bat                ← Script de compilation (double-clic)
├── assets/
│   ├── O-MTBig.png          ← Logo page d'accueil
│   └── O-MTSmall.png        ← Icône (titlebar + tray)
├── config/
│   ├── version.json         ← Numéro de version (modifiable)
│   ├── changelog.json       ← Changelog (modifiable)
│   ├── settings.json        ← Chemin UO (auto-généré)
│   ├── Dungeon.json         ← Polygones donjons
│   └── Wilderness.json      ← Zones wilderness (Coming Soon)
├── data/                    ← Sessions & XP (auto-généré)
└── scripts/
    ├── OMT_START.razor
    └── OMT_END.razor
```

---

## Modifier la version

Édite `config/version.json` :
```json
{ "version": "0.2" }
```
Puis recompile avec `build.bat`.

---

## Modifier le changelog

Édite `config/changelog.json` — ajoute une entrée en tête de liste :
```json
[
  {
    "version": "0.2",
    "date": "2026-06-01",
    "changes": ["Nouvelle fonctionnalité X", "Correction bug Y"]
  }
]
```
