#!/usr/bin/env python3
"""
Regenerates index.html, cases.html and sitemap.xml from the case pages.

Each case page carries its own listing metadata in the head:

    <meta name="mc:id"       content="MC-031">
    <meta name="mc:band"     content="Hours">      Hours | Days | Months | Years
    <meta name="mc:group"    content="Emergency">  filter chip
    <meta name="mc:interval" content="on arrival">
    <meta name="mc:note"     content="sitting forward to breathe">
    <meta name="mc:title"    content="...">
    <meta name="mc:dek"      content="...">

Add a case page with those tags and everything else updates itself.
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

WORDS = {20:'Twenty',21:'Twenty-one',22:'Twenty-two',23:'Twenty-three',24:'Twenty-four',
         25:'Twenty-five',26:'Twenty-six',27:'Twenty-seven',28:'Twenty-eight',29:'Twenty-nine',
         30:'Thirty',31:'Thirty-one',32:'Thirty-two',33:'Thirty-three',34:'Thirty-four',
         35:'Thirty-five',36:'Thirty-six',37:'Thirty-seven',38:'Thirty-eight'}


def rank(interval):
    t = interval.lower().strip()
    if t in ("within hours", "hours"):
        return 0.5
    num = re.search(r"[\d,]+(?:\.\d+)?", t)
    n = float(num.group(0).replace(",", "")) if num else 0.0
    if "min" in t:                   return n / 60
    if re.search(r"\bh\b|hour", t):  return n
    if "day" in t:                   return n * 24
    if "week" in t:                  return n * 168
    if "month" in t:                 return n * 730
    if re.match(r"^\s*(since\s+)?\d{3,4}\s*$", t) or "since" in t:
        return 9e8
    if "year" in t or "yr" in t:
        return n * 8760 if n else 8.5e8
    return 8e8


def meta(page, key, default=""):
    m = re.search(rf'<meta name="mc:{key}" content="([^"]*)"', page)
    return html.unescape(m.group(1)) if m else default


def collect():
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "case-*.html"))):
        s = open(path, encoding="utf-8").read()
        if 'name="mc:band"' not in s:
            print("  skipping", os.path.basename(path), "(no mc: tags)")
            continue
        d = re.search(r'"datePublished": "([\d-]+)"', s)
        out.append(dict(
            file=os.path.basename(path), slug=os.path.basename(path)[:-5],
            mc=meta(s, "id"), band=meta(s, "band"), group=meta(s, "group"),
            interval=meta(s, "interval"), note=meta(s, "note"),
            title=meta(s, "title"), dek=meta(s, "dek"),
            date=d.group(1) if d else datetime.date.today().isoformat(),
            hasfig='<figure class="fig"' in s,
            fig=(re.search(r'<figure class="fig".*?src="([\w./-]+)"', s, re.S).group(1)
                 if '<figure class="fig"' in s else ''),
            figcap=(re.search(r'<figure class="fig".*?<span class="lab">(.*?)</span>', s, re.S).group(1)
                    if '<figure class="fig"' in s else ''),
        ))
    return out


def row(c):
    fig = '<span class="hasfig"></span>' if c["hasfig"] else ""
    return (f'<li data-spec="{c["group"]}"><a class="row" href="/{c["slug"]}">'
            f'<span class="t">{html.escape(c["interval"])}'
            f'<small>{html.escape(c["note"])}</small></span>'
            f'<span><span class="meta"><span>{c["mc"]}</span>'
            f'<span>{c["group"]}</span>{fig}</span>'
            f'<span class="ti">{html.escape(c["title"])}</span>'
            f'<span class="dek">{html.escape(c["dek"])}</span></span></a></li>')


def build():
    cases = collect()
    if not cases:
        print("no cases found"); return 1
    n = len(cases)
    nfig = len(glob.glob(os.path.join(ROOT, "*.svg")))
    counts = {}
    for c in cases:
        counts[c["group"]] = counts.get(c["group"], 0) + 1

    # ---------------- cases.html ----------------
    p = os.path.join(ROOT, "cases.html")
    s = open(p, encoding="utf-8").read()

    bands_html = ""
    for band in BANDS:
        inband = sorted([c for c in cases if c["band"] == band], key=lambda c: rank(c["interval"]))
        if not inband:
            continue
        bands_html += (f'<section class="band">\n<div class="band-h"><h2>{band}</h2>'
                       f'<span>{BAND_BLURB[band]}</span></div>\n<ol>\n'
                       + "\n".join(row(c) for c in inband) + "\n</ol>\n</section>\n")

    plates = ""
    for c in sorted(cases, key=lambda c: c["mc"], reverse=True):
        if not c["fig"]:
            continue
        plates += (f'<a class="plate" href="/{c["slug"]}" data-spec="{c["group"]}">'
                   f'<div class="plate-h"><b>{c["mc"]}</b>'
                   f'<span class="t2">{html.escape(c["interval"])}</span></div>'
                   f'<div class="plate-i"><img src="{c["fig"]}" loading="lazy" decoding="async" '
                   f'alt="{html.escape(c["figcap"])}"></div></a>\n')

    views = ('<div class="mainwrap">\n\n<div id="tl">\n' + bands_html.rstrip() +
             '\n</div>\n\n<div id="figs">\n' + plates + '</div>\n\n</div>')

    first = s.index('<div class="mainwrap">')
    last = s.index('</main>')
    s = s[:first] + views + "\n" + s[last:]

    chips = f'<button aria-pressed="true" data-spec="">All <b>{n}</b></button>'
    for g in GROUPS:
        if g in counts:
            chips += f'<button aria-pressed="false" data-spec="{g}">{g} <b>{counts[g]}</b></button>'
    s = re.sub(r'(<div class="chips" id="chips">).*?(</div>)',
               lambda m: m.group(1) + chips + m.group(2), s, count=1, flags=re.S)

    s = re.sub(r'Search \d+ cases', f'Search {n} cases', s)
    s = re.sub(r'(<div><b>)\d+(</b><span class="lab">Cases published)', lambda m: m.group(1)+str(n)+m.group(2), s)
    s = re.sub(r'(<div><b>)\d+(</b><span class="lab">Original diagrams)', lambda m: m.group(1)+str(nfig)+m.group(2), s)
    s = re.sub(r'\b(Twenty|Thirty)(-[a-z]+)? cases, ordered by the clock',
               f"{WORDS.get(n, str(n))} cases, ordered by the clock", s)
    s = s.replace('Every case turns on an interval', 'Almost every case turns on an interval')
    s = s.replace('Almost Almost every', 'Almost every')
    open(p, "w", encoding="utf-8").write(s)

    # ---------------- index.html ----------------
    p = os.path.join(ROOT, "index.html")
    s = open(p, encoding="utf-8").read()
    latest = sorted(cases, key=lambda c: (c["date"], c["mc"]), reverse=True)[:6]
    s = re.sub(r'(<ol>).*?(</ol>)',
               lambda m: m.group(1) + "\n" + "\n".join(row(c) for c in latest) + "\n" + m.group(2),
               s, count=1, flags=re.S)
    s = re.sub(r'<b>\d+</b>cases published', f'<b>{n}</b>cases published', s)
    s = re.sub(r'<b>\d+</b>original diagrams', f'<b>{nfig}</b>original diagrams', s)
    s = re.sub(r'All \d+, by interval', f'All {n}, by interval', s)
    s = s.replace('Every case turns on an interval', 'Almost every case turns on an interval')
    s = s.replace('Almost Almost every', 'Almost every')
    open(p, "w", encoding="utf-8").write(s)

    # ---------------- sitemap.xml ----------------
    today = datetime.date.today().isoformat()
    urls = [("", "weekly", "1.0", today), ("cases", "weekly", "0.9", today)]
    for c in sorted(cases, key=lambda c: c["mc"], reverse=True):
        urls.append((c["slug"], "monthly", "0.8", c["date"]))
    for f in ["editorial", "about", "disclaimer", "privacy", "contact"]:
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
