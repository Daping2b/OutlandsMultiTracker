"""
Outlands Multi Tracker — Updater v4
Optimized: pre-extracted support, os.replace atomic, relaunch before cleanup.
Usage: Updater.exe <zip_path> <install_dir> <exe_name> [--pre-extracted <dir>]
"""
import sys, os, zipfile, shutil, time, subprocess, threading
from pathlib import Path

def main():
    if len(sys.argv) < 4:
        sys.exit(1)

    zip_path    = Path(sys.argv[1])
    install_dir = Path(sys.argv[2])
    exe_name    = sys.argv[3]
    flag_path   = install_dir / "_just_updated"
    tmp_dir     = install_dir / "_update_tmp"
    main_exe    = install_dir / exe_name

    # ── Pre-extracted dir ─────────────────────────────────────────────────────
    pre_dir = None
    if "--pre-extracted" in sys.argv:
        idx = sys.argv.index("--pre-extracted")
        if idx + 1 < len(sys.argv):
            p = Path(sys.argv[idx + 1])
            if p.exists(): pre_dir = p

    # ── Wait for exe lock — 50ms polling, 3s max ──────────────────────────────
    for i in range(60):
        try:
            test = main_exe.with_suffix(".tmp_test")
            main_exe.rename(test)
            test.rename(main_exe)
            break
        except:
            time.sleep(0.05)

    # ── Get source files ──────────────────────────────────────────────────────
    if pre_dir and pre_dir.exists():
        src_root = pre_dir
    else:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir()
        with zipfile.ZipFile(str(zip_path), "r") as z:
            z.extractall(tmp_dir)
        src_root = tmp_dir

    entries = list(src_root.iterdir())
    src = entries[0] if len(entries) == 1 and entries[0].is_dir() else src_root

    # ── Copy files — os.replace() atomic ─────────────────────────────────────
    skip_dirs  = {"data"}
    skip_files = {"config/settings.json", "config\\settings.json"}
    errors     = []

    for item in src.rglob("*"):
        rel     = item.relative_to(src)
        rel_str = str(rel).replace(os.sep, "/")
        parts   = rel.parts
        if parts and parts[0].lower() in skip_dirs: continue
        if rel_str in skip_files: continue
        dest = install_dir / rel
        if item.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(3):
            try:
                os.replace(str(item), str(dest))
                break
            except PermissionError:
                if attempt < 2: time.sleep(0.1)
                else:
                    try: shutil.copyfile(str(item), str(dest))
                    except Exception as e2: errors.append(f"{rel}: {e2}")
            except Exception as e:
                try: shutil.copyfile(str(item), str(dest))
                except: errors.append(f"{rel}: {e}")
                break

    # ── Write flag ────────────────────────────────────────────────────────────
    flag_path.write_text("1", encoding="utf-8")

    # ── Relaunch IMMEDIATELY — before cleanup ─────────────────────────────────
    subprocess.Popen([str(main_exe)], cwd=str(install_dir))

    # ── Cleanup in background — doesn't delay relaunch ────────────────────────
    def cleanup():
        for d in [tmp_dir, pre_dir, install_dir / "_update_pre"]:
            if d and d.exists():
                try: shutil.rmtree(d, ignore_errors=True)
                except: pass
        try: zip_path.unlink()
        except: pass
    threading.Thread(target=cleanup, daemon=True).start()
    time.sleep(0.3)
    sys.exit(0)

if __name__ == "__main__":
    main()
