#!/usr/bin/env python3
"""
Regenerates index.html, cases.html and sitemap.xml from the case pages.

Every case page carries its own metadata in the head:

    <meta name="mc:id"       content="MC-026">
    <meta name="mc:band"     content="Hours">      Hours | Days | Months | Years
    <meta name="mc:group"    content="Emergency">  filter chip
    <meta name="mc:interval" content="0 h">        the big figure in the row
    <meta name="mc:note"     content="machine still attached">
    <meta name="mc:title"    content="...">
    <meta name="mc:dek"      content="...">

Add a new case page with those tags and everything else updates itself.
"""

import re, os, glob, html, sys, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = "https://medicasehub.com"

BANDS = ["Hours", "Days", "Months", "Years"]
BAND_BLURB = {
    "Hours":  "Where the tissue is still alive and the window is closing",
    "Days":   "Long enough for a drug or an infection to declare itself",
    "Months": "Healing itself becomes the injury",
    "Years":  "The interval no one was counting",
}
GROUPS = ["Reconstruction", "Children", "Diagnosis", "Infection",
          "Emergency", "Orthopaedics", "Anatomy", "History"]

# smaller number sorts earlier inside a band
def rank(band, interval):
    t = interval.lower()
    num = re.search(r"[\d,]+(?:\.\d+)?", t)
    n = float(num.group(0).replace(",", "")) if num else 0.0
    if t.strip() in ("within hours","hours"): return 0.5
    if "min" in t:                       return n / 60
    if re.search(r"\bh\b|hour", t):      return n
    if "day" in t:                       return n * 24
    if "week" in t:                      return n * 168
    if "month" in t:                     return n * 730
    if re.match(r"^\s*(since\s+)?\d{3,4}\s*$", t) or "since" in t:
        return 9e8              # bare eras sit at the end
    if "year" in t or "yr" in t:
        return n * 8760 if n else 8.5e8
    return 8e8                  # wordy intervals just after the numbered ones


def meta(page, key, default=""):
    m = re.search(rf'<meta name="mc:{key}" content="([^"]*)"', page)
    return html.unescape(m.group(1)) if m else default


def collect():
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "case-*.html"))):
        s = open(path, encoding="utf-8").read()
        if 'name="mc:band"' not in s:
            print(f"  skipping {os.path.basename(path)} (no mc: tags)")
            continue
        d = re.search(r'"datePublished": "([\d-]+)"', s)
        out.append(dict(
            file=os.path.basename(path),
            slug=os.path.basename(path)[:-5],
            mc=meta(s, "id"), band=meta(s, "band"), group=meta(s, "group"),
            interval=meta(s, "interval"), note=meta(s, "note"),
            title=meta(s, "title"), dek=meta(s, "dek"),
            date=d.group(1) if d else datetime.date.today().isoformat(),
            hasfig=("<figure class=\"fig\"" in s),
        ))
    return out


def row(c):
    fig = '<span class="hasfig"></span>' if c["hasfig"] else ""
    return (f'<li data-spec="{c["group"]}"><a class="row" href="{c["file"]}">'
            f'<span class="t">{html.escape(c["interval"])}'
            f'<small>{html.escape(c["note"])}</small></span>'
            f'<span><span class="meta"><span>{c["mc"]}</span>'
            f'<span>{c["group"]}</span>{fig}</span>'
            f'<span class="ti">{html.escape(c["title"])}</span>'
            f'<span class="dek">{html.escape(c["dek"])}</span></span></a></li>')


def swap(page, start_pat, end_pat, new):
    a = re.search(start_pat, page, re.S)
    b = re.search(end_pat, page[a.end():], re.S)
    return page[:a.end()] + new + page[a.end() + b.start():]


def build():
    cases = collect()
    if not cases:
        print("no cases found"); return 1
    n = len(cases)
    nfig = len(glob.glob(os.path.join(ROOT, "*.svg")))
    counts = {g: sum(1 for c in cases if c["group"] == g) for g in GROUPS}
    counts = {g: v for g, v in counts.items() if v}

    # ---------- cases.html ----------
    p = os.path.join(ROOT, "cases.html")
    s = open(p, encoding="utf-8").read()

    bands_html = ""
    for band in BANDS:
        inband = sorted([c for c in cases if c["band"] == band],
                        key=lambda c: rank(band, c["interval"]))
        if not inband:
            continue
        bands_html += (f'<section class="band">\n'
                       f'<div class="band-h"><h2>{band}</h2>'
                       f'<span>{BAND_BLURB[band]}</span></div>\n<ol>\n'
                       + "\n".join(row(c) for c in inband) + "\n</ol>\n</section>\n")

    first = s.index('<section class="band">')
    last = s.rindex('</section>', 0, s.index('</main>') if '</main>' in s else len(s)) + len('</section>')
    s = s[:first] + bands_html.rstrip() + s[last:]

    chips = f'<button aria-pressed="true" data-spec="">All <b>{n}</b></button>'
    for g in GROUPS:
        if g in counts:
            chips += f'<button aria-pressed="false" data-spec="{g}">{g} <b>{counts[g]}</b></button>'
    s = re.sub(r'(<div class="chips" id="chips">).*?(</div>)', lambda m: m.group(1) + chips + m.group(2),
               s, count=1, flags=re.S)
    s = re.sub(r'Search \d+ cases', f'Search {n} cases', s)
    open(p, "w", encoding="utf-8").write(s)

    # ---------- index.html ----------
    p = os.path.join(ROOT, "index.html")
    s = open(p, encoding="utf-8").read()
    latest = sorted(cases, key=lambda c: (c["date"], c["mc"]), reverse=True)[:6]
    s = re.sub(r'(<ol>).*?(</ol>)',
               lambda m: m.group(1) + "\n" + "\n".join(row(c) for c in latest) + "\n" + m.group(2),
               s, count=1, flags=re.S)
    s = re.sub(r'<b>\d+</b>cases published', f'<b>{n}</b>cases published', s)
    s = re.sub(r'<b>\d+</b>original diagrams', f'<b>{nfig}</b>original diagrams', s)
    s = re.sub(r'All \d+, by interval', f'All {n}, by interval', s)
    open(p, "w", encoding="utf-8").write(s)

    # ---------- sitemap.xml ----------
    today = datetime.date.today().isoformat()
    urls = [("", "weekly", "1.0", today), ("cases.html", "weekly", "0.9", today)]
    for c in sorted(cases, key=lambda c: c["mc"], reverse=True):
        urls.append((c["file"], "monthly", "0.8", c["date"]))
    for f in ["editorial.html", "about.html", "disclaimer.html", "privacy.html", "contact.html"]:
        if os.path.exists(os.path.join(ROOT, f)):
            urls.append((f, "yearly", "0.5", today))

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', ""]
    for loc, cf, pr, lm in urls:
        out += ["  <url>", f"    <loc>{SITE}/{loc}</loc>", f"    <lastmod>{lm}</lastmod>",
                f"    <changefreq>{cf}</changefreq>", f"    <priority>{pr}</priority>", "  </url>", ""]
    out.append("</urlset>")
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(out) + "\n")

    print(f"{n} cases, {nfig} diagrams")
    for b in BANDS:
        k = sum(1 for c in cases if c["band"] == b)
        if k: print(f"  {b:8} {k}")
    return 0


if __name__ == "__main__":
    sys.exit(build())
