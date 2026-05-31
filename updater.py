"""
Outlands Multi Tracker — Updater v3
Standalone exe that replaces the main app while it's closed.
Usage: Updater.exe <zip_path> <install_dir> <exe_name> [--pre-extracted <pre_dir>]
"""
import sys, os, zipfile, shutil, time, subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 4:
        print("Usage: Updater.exe <zip_path> <install_dir> <exe_name> [--pre-extracted <dir>]")
        sys.exit(1)

    zip_path    = Path(sys.argv[1])
    install_dir = Path(sys.argv[2])
    exe_name    = sys.argv[3]
    flag_path   = install_dir / "_just_updated"
    tmp_dir     = install_dir / "_update_tmp"
    main_exe    = install_dir / exe_name

    # Check for pre-extracted flag
    pre_extracted_dir = None
    if "--pre-extracted" in sys.argv:
        idx = sys.argv.index("--pre-extracted")
        if idx + 1 < len(sys.argv):
            pre_extracted_dir = Path(sys.argv[idx + 1])
            if not pre_extracted_dir.exists():
                pre_extracted_dir = None

    print(f"[Updater] zip={zip_path}")
    print(f"[Updater] dir={install_dir}")
    print(f"[Updater] exe={exe_name}")
    print(f"[Updater] pre-extracted={pre_extracted_dir}")

    # ── Wait for exe lock (polling 50ms, timeout 3s) ──────────────────────────
    for i in range(60):
        try:
            test = main_exe.with_suffix(".tmp_test")
            main_exe.rename(test)
            test.rename(main_exe)
            print(f"[Updater] Exe unlocked after {i * 50}ms")
            break
        except:
            time.sleep(0.05)
    else:
        print("[Updater] WARNING: exe may still be locked, proceeding anyway...")

    # ── Use pre-extracted dir or extract zip ──────────────────────────────────
    if pre_extracted_dir and pre_extracted_dir.exists():
        print("[Updater] Using pre-extracted files — skipping extraction")
        src_root = pre_extracted_dir
    else:
        print("[Updater] Extracting zip...")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir()
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmp_dir)
        src_root = tmp_dir

    # Find source root inside extracted dir
    entries = list(src_root.iterdir())
    src = entries[0] if len(entries) == 1 and entries[0].is_dir() else src_root
    print(f"[Updater] Source root: {src}")

    # ── Copy files — protected: data/ and settings.json ──────────────────────
    skip_dirs  = {"data"}
    skip_files = {"config/settings.json", "config\\settings.json"}

    print("[Updater] Copying files...")
    errors = []
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
            except PermissionError as e:
                if attempt < 2:
                    time.sleep(0.1)
                else:
                    try: shutil.copyfile(str(item), str(dest))
                    except Exception as e2: errors.append(f"{rel}: {e2}")

    if errors:
        print(f"[Updater] {len(errors)} file(s) could not be copied:")
        for e in errors: print(f"  {e}")

    # ── Write flag then cleanup ───────────────────────────────────────────────
    flag_path.write_text("1", encoding="utf-8")
    print("[Updater] Flag written.")

    # Cleanup
    for d in [tmp_dir, pre_extracted_dir, install_dir / "_update_pre"]:
        if d and d.exists():
            try: shutil.rmtree(d, ignore_errors=True)
            except: pass
    try: zip_path.unlink()
    except: pass

    # ── Relaunch immediately ──────────────────────────────────────────────────
    print(f"[Updater] Launching {main_exe}")
    subprocess.Popen([str(main_exe)], cwd=str(install_dir))
    print("[Updater] Done!")
    sys.exit(0)

if __name__ == "__main__":
    main()
