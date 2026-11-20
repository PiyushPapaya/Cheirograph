#!/usr/bin/env python3
"""run_all_checks.py - one command that proves the repo is healthy.

Checks (one PASS/FAIL line each, exit 1 if any fails):
  a) the three dashboard copies are byte-identical (md5)
  b) every tools/verify_*.mjs runs under node (verify_touch_js.mjs is skipped:
     verify_touch_model.py runs it with its fixture)
  c) every tools/verify_*.py passes
  d) make_synthetic_batch.py output passes check_dataset.py
  e) no dead relative links in tracked .md files
  f) Data/ mirrors every tracked data/firmware/image/html file of a stage folder

Standard library only. Run from anywhere:  python tools/run_all_checks.py
"""
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
DASH = [
    TOOLS / "handrig_dashboard.html",
    ROOT / "08-ble-wireless-dashboard" / "handrig_dashboard.html",
    ROOT / "Data" / "html" / "08-ble-wireless-dashboard__handrig_dashboard.html",
]
# extension -> Data/ subfolder
MIRROR = {".csv": "csv", ".json": "csv", ".ino": "firmware", ".cpp": "firmware",
          ".png": "images", ".jpg": "images", ".jpeg": "images", ".gif": "images",
          ".html": "html"}


def run(cmd):
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def tracked():
    rc, out = run(["git", "ls-files"])
    return [l for l in out.splitlines() if l] if rc == 0 else []


def check_md5():
    sums = {}
    for f in DASH:
        sums[f] = hashlib.md5(f.read_bytes()).hexdigest() if f.exists() else None
    if len(set(sums.values())) == 1 and None not in sums.values():
        return True, "3 copies match"
    return False, ", ".join(f"{f.relative_to(ROOT)}={h}" for f, h in sums.items())


def check_scripts(pattern, launcher, skip=()):
    fails, n = [], 0
    for f in sorted(TOOLS.glob(pattern)):
        if f.name in skip:
            continue
        n += 1
        rc, out = run(launcher + [str(f)])
        if rc != 0:
            fails.append(f"{f.name}: {out.strip().splitlines()[-1] if out.strip() else 'exit ' + str(rc)}")
    return not fails, f"{n} scripts" if not fails else "; ".join(fails)


def check_synthetic():
    with tempfile.TemporaryDirectory() as tmp:
        rc, out = run([sys.executable, str(TOOLS / "make_synthetic_batch.py"), "--out", tmp])
        if rc != 0:
            return False, "make_synthetic_batch failed: " + out.strip()[-200:]
        rc, out = run([sys.executable, str(TOOLS / "check_dataset.py"), tmp])
        ok = rc == 0 and "RESULT: PASS" in out
        return ok, "RESULT: PASS" if ok else out.strip()[-300:]


def check_links(files):
    dead = []
    for rel in files:
        if not rel.endswith(".md"):
            continue
        md = ROOT / rel
        if not md.exists():
            continue
        text = re.sub(r"```.*?```", "", md.read_text(encoding="utf8", errors="replace"), flags=re.S)
        for m in re.finditer(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", text):
            link = m.group(1)
            if re.match(r"^([a-z]+:|#|//)", link, re.I):
                continue
            target = unquote(link.split("#")[0].split("?")[0])
            if target and not (md.parent / target).exists():
                dead.append(f"{rel} -> {link}")
    return not dead, f"{len(dead)} dead" if dead else "no dead links", dead


def check_mirror(files):
    gaps = []
    for rel in files:
        parts = rel.split("/")
        if len(parts) < 2 or not re.match(r"^\d\d-", parts[0]):
            continue
        sub = MIRROR.get(Path(rel).suffix.lower())
        if not sub:
            continue
        mirror = f"{sub}/{parts[0]}__{Path(rel).name}"
        if not (ROOT / "Data" / mirror).exists():
            gaps.append(f"{rel} -> Data/{mirror}")
    return not gaps, f"{len(gaps)} missing" if gaps else "all mirrored", gaps


def main():
    files = tracked()
    results = []

    def add(name, res):
        ok, msg = res[0], res[1]
        print(f"{'PASS' if ok else 'FAIL'} {name}: {msg}")
        for g in (res[2] if len(res) > 2 else []):
            print(f"       {g}")
        results.append(ok)

    add("dashboard copies (md5)", check_md5())
    add("verify_*.mjs", check_scripts("verify_*.mjs", ["node"], skip=("verify_touch_js.mjs",)))
    add("verify_*.py", check_scripts("verify_*.py", [sys.executable]))
    add("synthetic batch + check_dataset", check_synthetic())
    add("markdown links", check_links(files))
    add("Data/ mirror", check_mirror(files))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
