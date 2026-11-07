#!/usr/bin/env python3
"""analyze_touch_calibration.py: one report on a guided-calibration export.

Reads the JSON written by the dashboard's "Export calibration" (version 3 has the raw frames,
the event log and the session facts; the first real export, version 1, has only the holds and
templates). Prints link health, sensor health, missed or retried holds, spread and sample
count per hold, a replay of every hold through the detector (with what was read instead),
the radius of each template and what limited it, finger rolls, thumb offsets, the flat-check
drift, the self-test and errors. A second file adds a comparison. It ends with a short list
of what looks wrong, most serious first.

Usage:  python tools/analyze_touch_calibration.py <export.json> [earlier.json]
Needs numpy only.
"""
import json
import sys

import numpy as np

PAIR_FINGER = {"TI": 1, "TM": 2, "TR": 3, "TP": 4}
DIGITS = ["thumb", "index", "middle", "ring", "pinky"]
MAX_SPREAD = 0.1          # GUIDED_MAX_SPREAD in the dashboard
FLAT = np.array([1.0 if i % 3 == 2 else 0.0 for i in range(15)])
AXES = ["ax", "ay", "az", "gx", "gy", "gz"]
NAMES = ["hand", "thumb", "index", "middle", "ring", "pinky"]


def load(path):
    with open(path, encoding="utf8") as f:
        return json.load(f)


def digits_of(pairs):
    return [0] + [PAIR_FINGER[p] for p in pairs]


def ddist(digs, a, b):
    idx = [k for g in digs for k in range(g * 3, g * 3 + 3)]
    return float(np.linalg.norm(np.asarray(a)[idx] - np.asarray(b)[idx]))


def read_set(templates, row):
    """The dashboard's templateTouch with nothing touching before: pairs read as on."""
    on = set()
    for t in templates:
        if ddist(digits_of(t["pairs"]), t["mean"], row) < t["radius"]:
            on.update(t["pairs"])
    return on


def roll_from_fist(d):
    if not d[1] <= -0.2:
        return 0.0
    return float(max(-0.8, min(0.8, np.arctan(d[0] / d[1]))))


def pct(x):
    return f"{100 * x:.0f} %"


def section(title):
    print(f"\n== {title} ==")


class Report:
    def __init__(self, d, name):
        self.d, self.name = d, name
        self.problems = []   # (rank, text); lower rank = more serious
        self.missing = []

    def bad(self, rank, text):
        self.problems.append((rank, text))

    def need(self, key, why):
        if key not in self.d or self.d[key] is None:
            self.missing.append(f"{key} ({why})")
            return False
        return True


def header(r):
    d = r.d
    section("File")
    print(f"file: {r.name}")
    print(f"version: {d.get('version', 1)}   status: {d.get('status', 'not recorded')}   started: {d.get('date')}   ended: {d.get('endedAt', 'not recorded')}")
    sess = d.get("session")
    if sess:
        dash = sess.get("dashboard", {})
        print(f"dashboard: {dash.get('version')}  hash {dash.get('scriptHash')}  page {dash.get('page')}")
        print(f"browser: {sess.get('userAgent')}")
    else:
        print("dashboard / browser: not recorded (old export)")
    if "raw" not in d:
        r.missing.append("raw frames (stage holds are kept, the full stream is not)")
    for key, why in [("events", "event log"), ("session", "session facts: link rate, sensors, mount"),
                     ("marks", "stage start and end marks"), ("rolls", "finger rolls"), ("anchors", "thumb offsets"),
                     ("replay", "dashboard's own replay"), ("flatDeg", "flat check")]:
        if key not in d:
            r.missing.append(f"{key} ({why})")
    st = d.get("status", "complete")
    if st != "complete":
        r.bad(1, f"the run did not finish (status {st}): holds after the stop are missing")


def raw_arrays(d):
    raw = d.get("raw")
    if not raw or not raw.get("rows"):
        return None
    return np.array(raw["rows"], dtype=float)


def link_health(r):
    d, sess = r.d, r.d.get("session") or {}
    section("Link health")
    link = sess.get("link")
    if link:
        print(f"rate: min {link['hzMin']} Hz, mean {link['hzMean']} Hz over {link['hzSamples']} s")
        print(f"frames {link['frames']}, lost {link['lost']} ({link['lossPct']} %), bad frames {link['badFrames']}")
        if link["hzMean"] is not None and link["hzMean"] < 40:
            r.bad(2, f"link averaged {link['hzMean']} Hz, under the 40 Hz the integration needs")
        elif link["hzMin"] is not None and link["hzMin"] < 30:
            r.bad(3, f"link dipped to {link['hzMin']} Hz")
        if link["lossPct"] and link["lossPct"] > 5:
            r.bad(2, f"{link['lossPct']} % of frames lost")
        if link["badFrames"] > 50:
            r.bad(2, f"{link['badFrames']} bad frames (checksum rejects)")
        if link.get("bufferRefused"):
            r.bad(2, f"the frame buffer filled up and refused {link['bufferRefused']} frames: the end of the stream is missing")
        if link.get("eventsDropped"):
            r.bad(3, f"{link['eventsDropped']} events did not fit in the log")
    else:
        print("no session facts (old export)")
    a = raw_arrays(d)
    if a is None:
        return
    t = a[:, 0]
    dt = np.diff(t)
    good = dt[(dt > 0) & (dt < 1000)]
    print(f"raw stream: {len(a)} frames over {(t[-1] - t[0]) / 1000:.1f} s, firmware {1000 / np.median(good):.1f} Hz median spacing"
          f" (mean {1000 / good.mean():.1f} Hz)")
    gaps = int(np.sum(dt > 60))
    print(f"gaps over 60 ms between frames: {gaps}, longest {dt.max():.0f} ms")
    if gaps > 0.02 * len(a):
        r.bad(3, f"{gaps} gaps over 60 ms in the frame stream")
    mask = a[:, 1].astype(int)
    for s in range(6):
        inv = int(np.sum((mask >> s) & 1 == 0))
        if inv:
            print(f"  {NAMES[s]}: {inv} frames the firmware marked invalid")
            if inv > 0.01 * len(a):
                r.bad(2, f"{NAMES[s]} sensor: {inv} of {len(a)} frames invalid")


def sensor_health(r):
    d, sess = r.d, r.d.get("session") or {}
    section("Sensor health")
    sens = sess.get("sensors")
    a = raw_arrays(d)
    if not sens:
        print("no per-sensor facts (old export)")
    else:
        for s in sens:
            line = f"{s['name']:<7} cal={s['calibrated']} bad={s['bad']} flag='{s['flag']}' bias={s['bias']} noise={s['noise']}"
            print(line)
            print(f"        acc offset {s['accOffset']}  accel bias {s['accBias']}  clipped samples {s['clipSamples']}  latched drop {s['dropLatched']}")
            if s["bad"]:
                r.bad(1, f"{s['name']} is flagged bad: {s['flag']}")
            elif s["flag"]:
                r.bad(3, f"{s['name']} flagged: {s['flag']}")
            if not s["calibrated"]:
                r.bad(2, f"{s['name']} never calibrated")
            if s["clipSamples"]:
                r.bad(3, f"{s['name']} clipped {s['clipSamples']} gyro samples (rotation was lost)")
        m = sess.get("mount", {})
        print(f"hand mount: tilt {m.get('tiltDeg')} deg, psi {m.get('psiDeg')} deg, checked {m.get('checked')}")
        if m.get("tiltDeg") is not None and m["tiltDeg"] > 15:
            r.bad(3, f"hand IMU sits tipped {m['tiltDeg']} deg")
        if not m.get("checked"):
            r.bad(4, "hand mount angle was never checked (no whole-hand turn with straight fingers)")
        for c in sess.get("calibrations", []):
            lows = [x for x in c["sensors"] if x["n"] < 200]
            tag = f"  calibration '{c['kind']}' at {c['ms'] / 1000:.0f} s: sample counts {[x['n'] for x in c['sensors']]}"
            print(tag)
            for x in lows:
                r.bad(3, f"calibration '{c['kind']}': {NAMES[x['id']]} had only {x['n']} still samples")
    if a is not None:
        raw_faults(r, a)
        marks = d.get("marks") or []
        still = next((m for m in marks if m["name"] == "STILL" and m.get("f1") is not None), None)
        if still:
            blk = a[still["fHold"] or 0:still["f1"]]
            if len(blk) > 50:
                print("raw still window (calibration hold): mean |a| and gyro std per sensor")
                for s in range(6):
                    ac = blk[:, 2 + s * 6:5 + s * 6]
                    gy = blk[:, 5 + s * 6:8 + s * 6]
                    stuck = int(np.all(np.diff(ac, axis=0) == 0, axis=1).sum())
                    print(f"  {NAMES[s]:<7} |a| {np.linalg.norm(ac.mean(axis=0)):.3f} g   gyro std {gy.std(axis=0).round(2).tolist()}   identical consecutive frames {stuck}")
                    if stuck > 0.5 * len(blk):
                        r.bad(1, f"{NAMES[s]} reads the same value frame after frame (frozen register)")


def raw_faults(r, a):
    """Faults that show in the whole raw stream, not only in the still window."""
    ok = a[:, 1].astype(int)
    for s in range(6):
        v = a[:, 2 + s * 6:8 + s * 6]
        live = ((ok >> s) & 1) == 1
        same = np.all(np.diff(v, axis=0) == 0, axis=1) & live[1:] & live[:-1]
        run = best = 0
        for x in same:
            run = run + 1 if x else 0
            best = max(best, run)
        if best >= 50:
            print(f"  {NAMES[s]:<7} longest run of identical frames: {best}")
            r.bad(1, f"{NAMES[s]} reads the same value frame after frame ({best} in a row, frozen register)")
        g = np.abs(v[live][:, 3:6]) if live.any() else np.zeros((0, 3))
        if len(g) and g.max() >= 240:
            pinned = int(np.sum(g >= g.max() - 0.5))
            if pinned >= 5:
                print(f"  {NAMES[s]:<7} gyro pinned at {g.max():.0f} deg/s in {pinned} samples")
                r.bad(2, f"{NAMES[s]} gyro sits at {g.max():.0f} deg/s in {pinned} samples (clipped at the rail)")


def holds(r):
    d = r.d
    section("Holds")
    stages = d.get("stages", [])
    marks = d.get("marks") or []
    print(f"{'hold':<14}{'rows':>6}{'spread':>9}  notes")
    worst = []
    for s in stages:
        rows = np.array(s["rows"]) if s.get("rows") else None
        note = []
        if s["spread"] > 0.05:
            note.append("loose")
        if s["n"] < 60:
            note.append("few samples")
        if rows is not None and len(rows) > 2:
            sd = [float(np.sqrt(((rows[:, g * 3:g * 3 + 3] - rows[:, g * 3:g * 3 + 3].mean(0)) ** 2).sum(1).mean())) for g in range(5)]
            g = int(np.argmax(sd))
            if s["spread"] > 0.05:
                note.append(f"most movement in {DIGITS[g]} ({sd[g]:.3f})")
        att = s.get("attempt")
        if att and att > 1:
            note.append(f"kept on attempt {att}")
        print(f"{s['name']:<14}{s['n']:>6}{s['spread']:>9.4f}  {', '.join(note)}")
        if s["spread"] > 0.05:
            worst.append(s["name"])
    if worst:
        r.bad(4, f"loose holds (spread over 0.05, limit {MAX_SPREAD}): {', '.join(worst)}")
    missed = d.get("missed", [])
    print(f"missed holds: {missed or 'none'}")
    if missed:
        r.bad(2, f"missed holds: {', '.join(missed)}")
    retries = [m for m in marks if m.get("outcome") == "retry"]
    cancelled = [m for m in marks if m.get("outcome") == "cancelled"]
    if marks:
        print(f"retries: {len(retries)}")
        for m in retries:
            print(f"  {m['name']} attempt {m['attempt']}: {m.get('why')}")
        if retries:
            r.bad(3, f"{len(retries)} retried holds: " + ", ".join(sorted({m['name'] for m in retries})))
        if cancelled:
            print(f"cancelled stages: {[m['name'] for m in cancelled]}")
    else:
        print("retries: not recorded (old export)")
    expected = 16   # 17 steps, one of them the hand turn, which records no hold
    done = len(stages)
    if d.get("version", 1) >= 3 and d.get("status") == "complete" and done + len(missed) < expected:
        r.bad(3, f"only {done} holds recorded and {len(missed)} missed, for {expected} hold stages")


def replay(r):
    d = r.d
    section("Replay of every hold through the detector")
    tpl = d.get("templates", [])
    if not tpl:
        print("no templates in the file")
        return
    ok = 0
    total = 0
    bad_names = []
    for s in d.get("stages", []):
        if s["kind"] == "move" or not s.get("rows"):
            continue
        want = set(s.get("pairs") or []) if s["kind"] == "touch" else set()
        if s["kind"] == "touch" and not s.get("pairs"):
            want = set(s["name"].split(" ")[0].split("+"))
        rows = np.array(s["rows"])
        tally = {}
        for row in rows:
            k = "+".join(sorted(read_set(tpl, row)))
            tally[k] = tally.get(k, 0) + 1
        hit = tally.get("+".join(sorted(want)), 0)
        total += 1
        good = hit >= 0.7 * len(rows)
        ok += good
        instead = ", ".join(f"{k or 'nothing'} {pct(v / len(rows))}" for k, v in sorted(tally.items(), key=lambda kv: -kv[1]) if k != "+".join(sorted(want)))
        print(f"{'ok  ' if good else 'FAIL'} {s['name']:<14} read right {pct(hit / len(rows)):>6}" + (f"   read instead: {instead}" if instead else ""))
        if not good:
            bad_names.append(s["name"])
    print(f"{ok} of {total} holds read correctly (own replay)")
    if d.get("replay"):
        rp = d["replay"]
        print(f"dashboard's replay: {rp['ok']} of {rp['total']}  failed {rp['bad']}")
        if (rp["ok"], rp["total"]) != (ok, total):
            print("  (differs from the line above: the dashboard also counted holds that are not in 'stages')")
    if bad_names:
        r.bad(2, f"replay: {', '.join(bad_names)} not read back as themselves")


def radii(r):
    d = r.d
    section("Template radius and what limited it")
    tpl = d.get("templates", [])
    if not tpl:
        print("no templates in the file")
        return
    negs = {}
    for s in d.get("stages", []):
        if s["kind"] == "neg" and s.get("rows"):
            negs[s["name"]] = np.array(s["rows"]).mean(axis=0)
    negs["FLAT"] = FLAT
    print(f"{'pose':<16}{'spread':>8}{'3*spread':>9}{'radius':>8}  limited by / nearest others (half distance)")
    for t in tpl:
        name = "+".join(t["pairs"]) + " " + t["shape"]
        digs = digits_of(t["pairs"])
        near = sorted((ddist(digs, t["mean"], m) / 2, k) for k, m in negs.items())[:3]
        lim = t.get("limitedBy") or "its own spread (min 0.3)"
        print(f"{name:<16}{t['spread']:>8.4f}{3 * t['spread']:>9.3f}{t['radius']:>8.3f}  {lim};  " + ", ".join(f"{k} {v:.2f}" for v, k in near))
        if t.get("weak"):
            r.bad(3, f"{name}: weak (radius {t['radius']:.2f}, limited by {lim})")
    rr = sorted(t["radius"] for t in tpl)
    print(f"radius range {rr[0]:.3f} to {rr[-1]:.3f}")


def rolls_and_thumb(r):
    d = r.d
    section("Finger rolls")
    rolls = d.get("rolls")
    src = "from the export"
    if rolls is None:
        fist = next((s for s in d.get("stages", []) if s["name"] == "FIST" and s.get("rows")), None)
        if fist:
            m = np.array(fist["rows"]).mean(axis=0)
            rolls = [0.0] + [roll_from_fist(m[i * 3:i * 3 + 3]) for i in range(1, 5)]
            src = "recomputed from the FIST hold (not in the old export)"
    if rolls is None:
        print("no fist hold, no rolls")
    else:
        deg = [float(np.degrees(x)) for x in rolls]
        print(f"{src}: " + "  ".join(f"{n} {v:.0f}" for n, v in zip(DIGITS[1:], deg[1:])) + " deg")
        if any(abs(v) > 45 for v in deg[1:]):
            r.bad(3, "a finger roll over 45 deg: the fist hold may not have been a clean curl")
        if all(abs(v) < 5 for v in deg[1:]):
            r.bad(4, "all finger rolls under 5 deg: the fist hold may have been missing or too open")
    section("Thumb offsets")
    an = d.get("anchors")
    if not an:
        print("not in the file (old export)")
    else:
        for a in an:
            o = np.array(a["offset"])
            print(f"  {'+'.join(a.get('pairs') or []) or 'rest':<8}{a.get('shape') or '':<9} offset {o.round(2).tolist()}  |{np.linalg.norm(o):.2f}|")
        big = [a for a in an if a.get("pairs") and np.linalg.norm(a["offset"]) > 2.5]
        if big:
            r.bad(3, "thumb offset over 2.5 for " + ", ".join("+".join(a.get("pairs") or []) + " " + (a.get("shape") or "") for a in big) + " (about a finger length: check that hold)")
    section("Flat check")
    fd = d.get("flatDeg")
    if fd is None:
        flat = next((s for s in d.get("stages", []) if s["name"] == "FLATCHECK" and s.get("rows")), None)
        if flat:
            m = np.array(flat["rows"]).mean(axis=0)
            fd = float(np.mean([np.degrees(np.arccos(np.clip(m[i * 3 + 2], -1, 1))) for i in range(5)]))
            print(f"recomputed from the FLATCHECK hold: {fd:.1f} deg")
        else:
            print("no flat check in the file")
    else:
        print(f"a flat hand read {fd:.1f} deg bent at the end")
    if fd is not None and fd > 15:
        r.bad(2, f"drift: flat hand read {fd:.0f} deg bent at the end, templates may sit off")


def self_test(r):
    d = r.d
    section("Self-test")
    st = d.get("selfTest")
    if not st:
        print(f"not run (status {d.get('selfTestStatus', 'not recorded')})")
        r.bad(5, "self-test was not run")
        return
    for c in st:
        line = f"{'pass' if c['score'] >= 0.7 else 'FAIL'} {pct(c['score']):>6}  {c['text']}"
        if "sets" in c:
            n = c.get("n") or 0
            line += f"  frames {n}, skipped {c.get('skipped', 0)}; on-set: " + ", ".join(f"{k or 'nothing'} {v}" for k, v in sorted(c["sets"].items(), key=lambda kv: -kv[1]))
        print(line)
        if c.get("lastMeter"):
            print("        last distance/limit: " + "  ".join(f"{m['p']} {m['d']}/{m['r']}" for m in c["lastMeter"]))
    bad = [c for c in st if c["score"] < 0.7]
    if bad:
        r.bad(2, "self-test failed: " + ", ".join(c["text"] for c in bad))
    sess = d.get("session") or {}
    t = sess.get("touch") or {}
    if t.get("templatesFrom") and d.get("date") and t["templatesFrom"] != d["date"]:
        r.bad(3, "the self-test ran on templates from an earlier run, not the ones in this file")
    if t.get("stale"):
        r.bad(2, "the glove was re-zeroed after the templates were learned (stale)")


def errors(r):
    d = r.d
    section("Errors and events")
    errs = d.get("errors")
    if errs is None:
        print("errors: not recorded (old export)")
    else:
        print(f"errors: {len(errs)}")
        for e in errs:
            print(f"  [{e['kind']}] x{e['count']} {e['msg']}   {e.get('stack', '')[:160]}")
            r.bad(1, f"JS error {e['kind']} x{e['count']}: {e['msg']}")
    ev = d.get("events")
    if ev is None:
        return
    kinds = {}
    for e in ev:
        kinds[e["type"]] = kinds.get(e["type"], 0) + 1
    print("event counts: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
    for e in ev:
        if e["type"] in ("disconnect", "missed hold", "retry", "gyro clipping", "frames lost", "sensor state", "calibration", "run end", "zero orient"):
            extra = {k: v for k, v in e.items() if k not in ("ms", "frame", "type")}
            print(f"  {e['ms'] / 1000:8.1f} s  f{e['frame']:<6} {e['type']}: {extra}")
    if kinds.get("disconnect"):
        r.bad(1, "the glove disconnected during the run")
    if kinds.get("gyro clipping"):
        r.bad(3, f"gyro clipping reported {kinds['gyro clipping']} times")
    for e in ev:
        if e["type"] == "sensor state" and e["to"].startswith(("stale", "bad")) and e["from"] is not None:
            r.bad(2, f"{e['sensor']} went '{e['to']}' at {e['ms'] / 1000:.0f} s")
    if kinds.get("zero orient"):
        r.bad(3, "Zero orient was pressed during the record")


def compare(a, b):
    section(f"Comparison: {a.name} (new) against {b.name} (earlier)")
    da, db = a.d, b.d

    def by_name(d):
        return {s["name"]: s for s in d.get("stages", [])}

    sa, sb = by_name(da), by_name(db)
    print(f"holds kept: {len(sa)} vs {len(sb)}   missed: {da.get('missed')} vs {db.get('missed')}")
    print(f"{'hold':<14}{'spread':>9}{'then':>9}{'rows':>6}{'then':>6}")
    for k in sa:
        if k in sb:
            print(f"{k:<14}{sa[k]['spread']:>9.4f}{sb[k]['spread']:>9.4f}{sa[k]['n']:>6}{sb[k]['n']:>6}")
        else:
            print(f"{k:<14}{sa[k]['spread']:>9.4f}{'-':>9}{sa[k]['n']:>6}{'-':>6}   (new)")
    for k in sb:
        if k not in sa:
            print(f"{k:<14}{'-':>9}{sb[k]['spread']:>9.4f}{'-':>6}{sb[k]['n']:>6}   (only in the earlier file)")

    def tkey(t):
        return "+".join(t["pairs"]) + " " + t["shape"]

    ta = {tkey(t): t for t in da.get("templates", [])}
    tb = {tkey(t): t for t in db.get("templates", [])}
    print(f"\n{'template':<16}{'radius':>8}{'then':>8}")
    for k in ta:
        print(f"{k:<16}{ta[k]['radius']:>8.3f}" + (f"{tb[k]['radius']:>8.3f}" if k in tb else f"{'-':>8}"))
    for label, d in (("new", da), ("earlier", db)):
        rp = d.get("replay")
        fd = d.get("flatDeg")
        print(f"{label}: replay {rp['ok']}/{rp['total']}" if rp else f"{label}: replay not recorded", end="; ")
        print(f"flat drift {fd:.1f} deg" if fd is not None else "flat drift not recorded")
    la = (da.get("session") or {}).get("link")
    lb = (db.get("session") or {}).get("link")
    if la or lb:
        print(f"link mean rate: {la and la['hzMean']} vs {lb and lb['hzMean']} Hz; loss {la and la['lossPct']} vs {lb and lb['lossPct']} %")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    try:
        reports = [Report(load(p), p) for p in sys.argv[1:3]]
    except (OSError, ValueError) as e:
        print(f"cannot read the file: {e} (a cut-off download is not valid JSON)")
        return 1
    if not all(isinstance(x.d, dict) for x in reports):
        print("the file is not a calibration export (top level is not an object)")
        return 1
    r = reports[0]
    steps = [header, link_health, sensor_health, holds, replay, radii, rolls_and_thumb, self_test, errors]
    if len(reports) > 1:
        steps.append(lambda x: compare(x, reports[1]))
    for step in steps:
        try:
            step(r)
        except Exception as e:   # a partial or odd file must still give a report
            name = getattr(step, "__name__", "compare")
            print(f"  [{name}: stopped early, {type(e).__name__}: {e}; a key is missing or has the wrong type]")
            r.missing.append(f"{name}: {type(e).__name__} {e}")
            r.bad(4, f"section '{name}' could not be read fully ({type(e).__name__}: {e})")
    if r.missing:
        section("Missing from this file")
        for m in r.missing:
            print("  - " + m)
    section("What looks wrong, most serious first")
    if not r.problems:
        print("nothing flagged")
    for i, (_, text) in enumerate(sorted(r.problems, key=lambda p: p[0]), 1):
        print(f"{i}. {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
