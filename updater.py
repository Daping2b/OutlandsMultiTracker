"""
Outlands Multi Tracker — Updater
Standalone exe that replaces the main exe while it's closed.
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

    # Wait for main exe to release its lock (up to 15 seconds)
    for i in range(15):
        try:
            # Try to rename exe briefly to test if it's locked
            test = main_exe.with_suffix(".tmp_test")
            main_exe.rename(test)
            test.rename(main_exe)
            print(f"[Updater] Main exe unlocked after {i}s")
            break
        except:
            print(f"[Updater] Waiting for exe to close... ({i+1}s)")
            time.sleep(1)
    else:
        print("[Updater] WARNING: exe may still be locked, trying anyway...")

    # Extract zip
    print("[Updater] Extracting...")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir()

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(tmp_dir)

    # Find source root inside zip
    entries = list(tmp_dir.iterdir())
    src = entries[0] if len(entries) == 1 and entries[0].is_dir() else tmp_dir
    print(f"[Updater] Source root: {src}")

    # Protected paths — never overwrite
    skip_dirs  = {"data"}
    skip_files = {"config/settings.json", "config\\settings.json"}

    # Copy all files
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
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Retry up to 5 times for locked files
            for attempt in range(5):
                try:
                    shutil.copy2(item, dest)
                    break
                except PermissionError as e:
                    if attempt < 4:
                        time.sleep(0.5)
                    else:
                        errors.append(f"{rel}: {e}")

    if errors:
        print(f"[Updater] {len(errors)} files could not be copied:")
        for e in errors: print(f"  {e}")

    # Write flag AFTER all copies done
    flag_path.write_text("1", encoding="utf-8")
    print("[Updater] Flag written.")

    # Cleanup
    try: shutil.rmtree(tmp_dir)
    except: pass
    try: zip_path.unlink()
    except: pass

    # Relaunch main exe
    print(f"[Updater] Launching {main_exe}")
    time.sleep(0.5)
    subprocess.Popen([str(main_exe)], cwd=str(install_dir))
    print("[Updater] Done!")
    sys.exit(0)

if __name__ == "__main__":
    main()
