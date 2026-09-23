#!/usr/bin/env python3
"""Capture era-matched screenshots for the work.stevenjhubbard.com portfolio.

Live sites are shot as they stand today. Everything else is pulled from the
Wayback Machine at a timestamp inside the engagement, so each card shows the
site as it looked when Steven worked on it -- not whatever replaced it since.

Usage: python3 capture.py [id ...]      (no args = everything)
"""
import json, os, shutil, subprocess, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW  = os.path.join(HERE, "assets", "raw")
WEBP = os.path.join(HERE, "assets", "webp")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 2000, 1250          # 16:10, wide enough to run full-bleed on a 5K display

# Chrome's "site can't be reached" page renders at a very consistent ~34 KB at
# this size, and archive.org serves it freely once it decides you are hammering
# it. Every genuine capture so far has been 144 KB or more, so a floor here
# rejects both the error page and a page whose assets never loaded. A capture
# under this is a retry, not a result.
MIN_BYTES = 120_000
PAUSE = 20                 # seconds between shots, to stay under rate limiting

# id, live-url or None, wayback-target, wayback-timestamp
SHOTS = [
    ("mend",        "https://www.mendmedicalwear.com/", None, None),
    ("sjh",         "https://www.stevenjhubbard.com/",   None, None),
    ("eyeappeal",   "https://eyeappealinc.com/",        None, None),
    ("coupdetat",   "https://coupdetatsf.com/",         None, None),
    ("tivo",         None, "tivo.com",              "20211101"),
    ("lexmark",      None, "lexmark.com/en_us.html", "20221201"),
    ("tenx",         None, "ten-x.com",             "20161201"),
    ("chrome",       None, "chromeindustries.com",  "20150301"),
    ("thismoment",   None, "thismoment.com",        "20140301"),
    ("urbanair",     None, "urbanairmarket.com",    "20130601"),
    # eurorscg and horizon are Steven's own images (2026-09-22) -- not in SHOTS,
    # because a re-shoot would replace them with a dead Flash page / empty shell.
    ("moss",         None, "mossoutdoor.com",       "20110301"),
    ("nflashback",   None, "nationalflashback.com", "20190825"),  # 2000-08 is Flash; this is the 2019 portfolio
    ("nimblefish",   None, "nimblefish.com",        "20050601"),
    ("puzzletheory", None, "puzzletheory.com",      "20110201"),  # earliest surviving
    ("irhythm",      None, "irhythmtech.com",       "20190601"),
    ("digitalbrew",  None, "digitalbrewing.com",    "20090301"),
]


def _month_shift(ts, months):
    y, m = int(ts[:4]), int(ts[4:6])
    total = y * 12 + (m - 1) + months
    return "%04d%02d" % (total // 12, total % 12 + 1)


def cdx(target, ts, span=1):
    """Closest 200-status capture inside +/- `span` MONTHS of ts.

    The availability API accepts a timestamp and then cheerfully returns a
    capture a decade away -- it did exactly that for Lexmark, offering 2012
    for a 2022 engagement. CDX takes a real date range, so an out-of-era
    capture comes back as "none" instead of as a wrong answer.
    """
    # Month-precision bounds keep the index scan small. lexmark.com has
    # millions of captures and a whole-year range times the CDX server out.
    url = ("http://web.archive.org/cdx/search/cdx?url=%s&matchType=exact"
           "&from=%s&to=%s"
           "&filter=statuscode:200&filter=mimetype:text/html"
           "&collapse=timestamp:6&output=json&limit=120"
           % (urllib.parse.quote(target), _month_shift(ts, -span), _month_shift(ts, span)))
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            rows = json.load(r)
    except Exception as e:
        print("  ! cdx: %s" % e, flush=True)
        return None
    if len(rows) < 2:
        return None
    # rows[0] is the header. Pick the capture nearest the target date.
    stamps = [row[1] for row in rows[1:]]
    return min(stamps, key=lambda t: abs(int(t[:8]) - int(ts[:8])))


def wayback(target, ts):
    """Resolve the closest capture. Returns (url, timestamp) or (None, None).

    if_ suffix = iframe mode: the page without the Wayback toolbar chrome.
    """
    stamp = cdx(target, ts, 4) or cdx(target, ts, 12) or cdx(target, ts, 30)
    if not stamp:
        print("  ! no capture within 30 months of %s" % ts, flush=True)
        return None, None
    scheme = "https" if stamp >= "2016" else "http"
    # Only bare hosts get the trailing slash; a target carrying a path is
    # already complete (lexmark.com/en_us.html, say).
    tail = target if "/" in target else target + "/"
    return ("https://web.archive.org/web/%sif_/%s://%s" % (stamp, scheme, tail)), stamp


def reachable(url, tries=5):
    """True once archive.org actually serves the URL.

    Rate limiting is the failure mode that matters here: a burst of parallel
    captures gets refused, Chrome screenshots its own error page, and the file
    check passes on garbage. Ask first, and back off when the answer is no.
    """
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                if r.status == 200:
                    return True
        except Exception as e:
            print("  . not ready (%s)" % e, flush=True)
        wait = 5 * (2 ** i)
        print("  . backing off %ds" % wait, flush=True)
        time.sleep(wait)
    return False


def shoot(url, out):
    """Screenshot `url` into `out`. True if a plausible-sized file landed.

    Two things about headless Chrome drive this shape:

    1. It writes the PNG and then frequently declines to exit, so the file is
       the success signal, not the process. Poll for it and kill afterwards.
    2. Two Chromes sharing a --user-data-dir is an instant, silent failure --
       the second exits without writing anything. A killed-but-lingering
       process from an earlier run once took out a whole batch of eleven that
       way. Each shot therefore gets its own throwaway profile.
    """
    if os.path.exists(out):
        os.remove(out)
    profile = os.path.join(HERE, ".chrome-tmp", os.path.basename(out) + ".profile")
    os.makedirs(profile, exist_ok=True)
    proc = subprocess.Popen([
        CHROME, "--headless=old", "--disable-gpu", "--hide-scrollbars",
        "--no-sandbox", "--user-data-dir=" + profile,
        "--window-size=%d,%d" % (W, H),
        "--virtual-time-budget=25000",       # Wayback is slow; let assets land
        "--screenshot=" + out, url,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    size, stable = -1, 0
    for _ in range(90):                      # up to ~90s
        if proc.poll() is not None and os.path.exists(out):
            break
        if os.path.exists(out):
            now = os.path.getsize(out)
            # Two identical reads a second apart means the write finished.
            stable = stable + 1 if now == size and now > 0 else 0
            size = now
            if stable >= 2:
                break
        time.sleep(1)

    if proc.poll() is None:
        proc.kill(); proc.wait()
    shutil.rmtree(profile, ignore_errors=True)
    if not os.path.exists(out):
        return False
    size = os.path.getsize(out)
    if size < MIN_BYTES:
        print("  ! only %d KB — error page or unloaded assets" % (size // 1024), flush=True)
        os.remove(out)
        return False
    return True


def main():
    only = set(sys.argv[1:])
    os.makedirs(RAW, exist_ok=True); os.makedirs(WEBP, exist_ok=True)
    stamps, failed = {}, []

    for pid, live, target, ts in SHOTS:
        if only and pid not in only:
            continue
        png = os.path.join(RAW, pid + ".png")
        if os.path.exists(os.path.join(WEBP, pid + ".webp")) and not only:
            print("%-14s already captured, skipping" % pid, flush=True); continue
        if live:
            url, stamp = live, "live"
        else:
            url, stamp = wayback(target, ts)
            if not url:
                print("%-14s NO CAPTURE" % pid, flush=True); failed.append(pid); continue
        print("%-14s %s" % (pid, url), flush=True)

        if not live and not reachable(url):
            print("  ! archive.org would not serve it", flush=True)
            failed.append(pid); continue

        if not shoot(url, png):
            print("  ! screenshot failed", flush=True); failed.append(pid); continue

        subprocess.run(["cwebp", "-q", "82", "-quiet", png,
                        "-o", os.path.join(WEBP, pid + ".webp")], check=True)
        subprocess.run(["cwebp", "-q", "80", "-quiet", "-resize", "1000", "0", png,
                        "-o", os.path.join(WEBP, pid + "@sm.webp")], check=True)
        stamps[pid] = stamp
        print("  ok  %s  (%d KB)" % (stamp, os.path.getsize(png) // 1024), flush=True)
        time.sleep(PAUSE)

    path = os.path.join(HERE, "captures.json")
    merged = {}
    if os.path.exists(path):
        with open(path) as f:
            merged = json.load(f)
    merged.update(stamps)
    with open(path, "w") as f:
        json.dump(merged, f, indent=2, sort_keys=True)
    print("\ncaptured %d, failed %d %s" % (len(stamps), len(failed), failed or ""))


if __name__ == "__main__":
    main()
