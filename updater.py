"""
Outlands Multi Tracker — Updater v2
Standalone exe that replaces the main app while it's closed.
Usage: Updater.exe <zip_path> <install_dir> <exe_name>
"""
import sys, os, zipfile, shutil, time, subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 4:
        print("Usage: Updater.exe <zip_path> <install_dir> <exe_name>")
        sys.exit(1)

    zip_path    = Path(sys.argv[1])
    install_dir = Path(sys.argv[2])
    exe_name    = sys.argv[3]
    flag_path   = install_dir / "_just_updated"
    tmp_dir     = install_dir / "_update_tmp"
    main_exe    = install_dir / exe_name

    print(f"[Updater] zip={zip_path}")
    print(f"[Updater] dir={install_dir}")
    print(f"[Updater] exe={exe_name}")

    # ── Wait for exe lock to release (polling 50ms, timeout 3s) ──────────────
    # os._exit(0) in main app releases the lock almost instantly
    unlocked = False
    for i in range(60):  # 60 × 50ms = 3s max
        try:
            test = main_exe.with_suffix(".tmp_test")
            main_exe.rename(test)
            test.rename(main_exe)
            print(f"[Updater] Exe unlocked after {i * 50}ms")
            unlocked = True
            break
        except:
            time.sleep(0.05)
    if not unlocked:
        print("[Updater] WARNING: exe may still be locked, proceeding anyway...")

    # ── Extract zip ───────────────────────────────────────────────────────────
    print("[Updater] Extracting...")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir()

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(tmp_dir)

    # Find source root inside zip
    entries = list(tmp_dir.iterdir())
    src = entries[0] if len(entries) == 1 and entries[0].is_dir() else tmp_dir
    print(f"[Updater] Source root: {src}")

    # ── Copy files — os.replace() is atomic on Windows ───────────────────────
    # Protected: never overwrite user data or settings
    skip_dirs  = {"data"}
    skip_files = {"config/settings.json", "config\\settings.json"}

    print("[Updater] Copying files...")
    errors = []
    for item in src.rglob("*"):
        rel     = item.relative_to(src)
        rel_str = str(rel).replace(os.sep, "/")
        parts   = rel.parts

        if parts and parts[0].lower() in skip_dirs:
            continue
        if rel_str in skip_files:
            continue

        dest = install_dir / rel
        if item.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        # os.replace() is atomic and faster than shutil — retry up to 3x on lock
        for attempt in range(3):
            try:
                os.replace(str(item), str(dest))
                break
            except PermissionError as e:
                if attempt < 2:
                    time.sleep(0.1)
                else:
                    # Fallback: copyfile
                    try:
                        shutil.copyfile(str(item), str(dest))
                    except Exception as e2:
                        errors.append(f"{rel}: {e2}")

    if errors:
        print(f"[Updater] {len(errors)} file(s) could not be copied:")
        for e in errors:
            print(f"  {e}")

    # ── Write flag then cleanup ───────────────────────────────────────────────
    flag_path.write_text("1", encoding="utf-8")
    print("[Updater] Flag written.")

    try: shutil.rmtree(tmp_dir, ignore_errors=True)
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
