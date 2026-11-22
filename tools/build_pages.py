"""Build the Out of Focus art guide pages from the paintings data in index.html.

Creates (inside the site folder):
  paintings/<slug>.html   one page per painting
  artists/<slug>.html     one page per artist with a written note
  guides/<style>.html     one page per category
  guides/index.html       the Art guides hub (categories + every painting A-Z)
  thumbs/<img>.jpg        small images for the grids
  sitemap.xml, robots.txt
Run again after adding paintings; it rewrites everything it made.
"""
import json, os, re, sys, unicodedata, html, shutil
from collections import defaultdict
from PIL import Image

SITE = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/out-of-focus-daily"
BASE = "https://out-of-focus-games.com"
sys.path.insert(0, os.path.dirname(__file__))
from guide_text import CATEGORIES, ARTISTS

CAT_ORDER = ["famous", "renaissance", "baroque", "dutch", "romanticism", "impressionism", "postimpressionism"]
E = lambda s: html.escape(str(s), quote=True)

src = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
P = json.loads(re.search(r"const PAINTINGS\s*=\s*(\[.*?\n\]);", src, re.S).group(1))

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s or "painting"

def clean_title(p):
    return p.get("display") or p["title"]

# unique slugs
seen = set()
for p in P:
    base = slugify(re.sub(r"\s*\(.*?\)\s*$", "", clean_title(p)))
    slug, n = base, 2
    if slug in seen:
        slug = f"{base}-{slugify(p['artist'].split()[-1])}"
    while slug in seen:
        slug = f"{base}-{n}"; n += 1
    seen.add(slug); p["_slug"] = slug

artist_slug = {a: slugify(a) for a in ARTISTS}
by_artist = defaultdict(list); by_cat = defaultdict(list)
for p in P:
    by_artist[p["artist"]].append(p)
    for c in p["cats"]: by_cat[c].append(p)

# ---------- thumbnails ----------
os.makedirs(os.path.join(SITE, "thumbs"), exist_ok=True)
for p in P:
    t = os.path.join(SITE, "thumbs", p["img"] + ".jpg")
    if not os.path.exists(t):
        im = Image.open(os.path.join(SITE, "images", p["img"] + ".jpg")).convert("RGB")
        im.thumbnail((420, 420), Image.LANCZOS)
        im.save(t, quality=82, optimize=True, progressive=True)

# ---------- shared page frame ----------
HEAD_EXTRA = '''<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#18241f">
<link rel="icon" type="image/png" sizes="48x48" href="/icons/favicon-48.png">
<link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32.png">
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400..800;1,6..96,400..700&family=Instrument+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/site.css">
<link rel="stylesheet" href="/guides.css">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3316593120945895"
     crossorigin="anonymous"></script>
'''
FOOT = '''<footer><a href="/">Play</a><a href="/guides/">Art guides</a><a href="/how-to-play.html">How to play</a><a href="/about.html">About</a><a href="/privacy.html">Privacy</a><a href="/contact.html">Contact</a></footer>'''
REG = '''<script>
if ("serviceWorker" in navigator && /(^|\\.)out-of-focus-games\\.com$|netlify\\.app$/.test(location.hostname)) {
  addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
}
</script>'''

def page(path, title, desc, body, image=None, crumbs=None):
    url = f"{BASE}/{path}".replace("/index.html", "/")
    og_img = f"{BASE}/images/{image}.jpg" if image else f"{BASE}/og.png"
    crumb_html = ""
    if crumbs:
        crumb_html = '<nav class="crumbs">' + ' <span aria-hidden="true">›</span> '.join(
            f'<a href="{h}">{E(t)}</a>' if h else E(t) for t, h in crumbs) + '</nav>'
    doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:image" content="{og_img}">
<meta name="twitter:card" content="summary_large_image">
{HEAD_EXTRA}</head>
<body>
<div class="page wide">
  <div class="top"><a class="logo" href="/">Out of <b>Focus</b></a><a class="play" href="/">Play today’s puzzle</a></div>
  {crumb_html}
{body}
  {FOOT}
</div>
{REG}
</body>
</html>
'''
    full = os.path.join(SITE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(doc)
    return url

def card(p):
    return (f'<a class="card" href="/paintings/{p["_slug"]}.html"><img src="/thumbs/{p["img"]}.jpg" alt="{E(clean_title(p))} by {E(p["artist"])}" loading="lazy">'
            f'<span class="ct">{E(clean_title(p))}</span><span class="ca">{E(p["artist"])}</span></a>')

def grid(items): return '<div class="grid">' + "".join(card(p) for p in items) + '</div>'

MAIN_PRIORITY = ["dutch", "romanticism", "postimpressionism", "impressionism", "renaissance", "baroque", "famous"]
def mainstyle(cats):
    return next(c for c in MAIN_PRIORITY if c in cats)

def year_key(p):
    m = re.search(r"\d{4}", p["date"]); return int(m.group()) if m else 9999

urls = []
for d in ["paintings", "artists", "guides"]:
    shutil.rmtree(os.path.join(SITE, d), ignore_errors=True)

# ---------- painting pages ----------
for p in P:
    t = clean_title(p)
    cats = [c for c in CAT_ORDER if c in p["cats"]]
    style_links = ", ".join(f'<a href="/guides/{CATEGORIES[c]["path"]}.html">{E(CATEGORIES[c]["name"])}</a>' for c in cats)
    artist_html = E(p["artist"])
    if p["artist"] in ARTISTS:
        artist_html = f'<a href="/artists/{artist_slug[p["artist"]]}.html">{E(p["artist"])}</a>'
    more_artist = [q for q in by_artist[p["artist"]] if q is not p]
    sections = []
    museum = p.get("museum") or ""
    place = museum if museum.startswith(("The ", "Tate", "Santa")) else "the " + museum
    where = f' It is {p["medium"][0].lower() + p["medium"][1:]}' + (f', and you can see it today at {place}.' if museum and not museum.lower().startswith(("several","five","versions")) else '.')
    when = p["date"]
    if when.startswith("c. "): when = "around " + when[3:]
    elif "century" in when: when = "the " + when
    who = p["artist"] if not p["artist"].lower().startswith(("workshop", "after", "attributed", "unknown", "florentine", "spanish painter")) else "The artist"
    intro = f'{who} made <em>{E(t)}</em> {"" if when.startswith("around") else "in "}{E(when)}.{E(where)}'
    sections.append(f'<h2>About this painting</h2>\n  <p>{intro}</p>\n  <p>{E(p["fact"])}</p>')
    if p["artist"] in ARTISTS:
        sections.append(f'<h2>About the artist</h2>\n  <p>{E(ARTISTS[p["artist"]])} <a href="/artists/{artist_slug[p["artist"]]}.html">More about {E(p["artist"])}</a></p>')
    if cats:
        main = mainstyle(cats)
        cd = CATEGORIES[main]
        sections.append(f'<h2>The style: {E(cd["name"])}</h2>\n  <p>{E(cd["lede"])} <a href="/guides/{cd["path"]}.html">Read the {E(cd["name"])} guide</a></p>')
    if more_artist:
        sections.append(f'<h2>More by {E(p["artist"])}</h2>\n  {grid(sorted(more_artist, key=year_key)[:6])}')
    if cats:
        main = mainstyle(cats)
        pool = [q for q in by_cat[main] if q is not p and q["artist"] != p["artist"]]
        # a stable, varied pick: step through the list from this painting's position
        if pool:
            k = (sum(map(ord, p["img"])) % len(pool))
            pick = [pool[(k + i * 7) % len(pool)] for i in range(min(6, len(pool)))]
            pick = list(dict.fromkeys(id(x) for x in pick))
            pick = [next(q for q in pool if id(q) == i) for i in pick]
            sections.append(f'<h2>More {E(CATEGORIES[main]["name"])} paintings</h2>\n  {grid(pick)}')
    body = f'''  <article class="painting">
  <h1>{E(t)}</h1>
  <p class="byline">{artist_html} <span>({E(p["life"])})</span></p>
  <figure class="art"><img src="/images/{p["img"]}.jpg" alt="{E(t)} by {E(p["artist"])}"></figure>
  <dl class="facts">
    <div><dt>Date</dt><dd>{E(p["date"])}</dd></div>
    <div><dt>Medium</dt><dd>{E(p["medium"])}</dd></div>
    <div><dt>Where to see it</dt><dd>{E(p.get("museum") or "")}</dd></div>
    {f'<div><dt>Style</dt><dd>{style_links}</dd></div>' if style_links else ''}
  </dl>
  <div class="cta">Could you name it from a blurry mosaic? <a href="/">Play today’s Out of Focus puzzle</a></div>
  {chr(10).join("  " + s for s in sections)}
  </article>'''
    desc = f'{t} by {p["artist"]} ({p["date"]}). {p["fact"]}'
    if len(desc) > 300: desc = desc[:297].rsplit(" ", 1)[0] + "…"
    crumbs = [("Art guides", "/guides/")]
    if cats:
        main = mainstyle(cats)
        crumbs.append((CATEGORIES[main]["name"], f'/guides/{CATEGORIES[main]["path"]}.html'))
    crumbs.append((t, None))
    urls.append(page(f'paintings/{p["_slug"]}.html', f'{t} by {p["artist"]} | Out of Focus', desc, body, p["img"], crumbs))

# ---------- artist pages ----------
for a, note in ARTISTS.items():
    works = sorted(by_artist.get(a, []), key=year_key)
    if not works: continue
    life = works[0]["life"]
    body = f'''  <h1>{E(a)}</h1>
  <p class="lede">{E(life)}</p>
  <p>{E(note)}</p>
  <h2>{len(works)} painting{"s" if len(works) != 1 else ""} by {E(a)} in Out of Focus</h2>
  {grid(works)}
  <div class="cta">Think you’d know a {E(a.split()[-1])} anywhere? <a href="/">Play today’s puzzle</a></div>'''
    urls.append(page(f'artists/{artist_slug[a]}.html', f'{a}: paintings and biography | Out of Focus', note[:290], body, works[0]["img"],
                     [("Art guides", "/guides/"), (a, None)]))

# ---------- category guides ----------
for c in CAT_ORDER:
    cd = CATEGORIES[c]; works = sorted(by_cat[c], key=year_key)
    if not works: continue
    artists_here = []
    for q in works:
        if q["artist"] in ARTISTS and q["artist"] not in artists_here: artists_here.append(q["artist"])
    key_artists = ""
    if artists_here:
        key_artists = '<h2>Key artists</h2>\n  <ul class="artists">' + "".join(
            f'<li><a href="/artists/{artist_slug[a]}.html">{E(a)}</a></li>' for a in artists_here) + '</ul>'
    body = f'''  <h1>{E(cd["name"])}</h1>
  <p class="lede">{E(cd["dates"])} · {E(cd["lede"])}</p>
  {"".join(f"<p>{E(par)}</p>" for par in cd["body"])}
  <h2>What to look for</h2>
  <ul>{"".join(f"<li>{E(x)}</li>" for x in cd["look"])}</ul>
  {key_artists}
  <div class="cta">Test yourself: <a href="/?cat={c}">play a game of {E(cd["name"])}</a></div>
  <h2>All {len(works)} {E(cd["name"])} paintings in the game</h2>
  {grid(works)}'''
    urls.append(page(f'guides/{cd["path"]}.html', f'{cd["name"]}: a guide with {len(works)} paintings | Out of Focus',
                     f'{cd["lede"]} A short guide to {cd["name"]}, its key artists and {len(works)} paintings.', body, works[0]["img"],
                     [("Art guides", "/guides/"), (cd["name"], None)]))

# ---------- guides hub ----------
letters = defaultdict(list)
for p in sorted(P, key=lambda q: re.sub(r"^(the|a|an)\s+", "", clean_title(q).lower())):
    k = re.sub(r"^(the|a|an)\s+", "", clean_title(p), flags=re.I)[:1].upper()
    letters[k if k.isalpha() else "#"].append(p)
COVERS = {"famous": "The Starry Night", "renaissance": "The Birth of Venus", "baroque": "Las Meninas", "dutch": "Girl with a Pearl Earring",
          "romanticism": "Wanderer above the Sea of Fog", "impressionism": "Impression, Sunrise", "postimpressionism": "A Sunday on La Grande Jatte — 1884"}
def cover(c):
    return next((q for q in by_cat[c] if q["title"] == COVERS.get(c)), by_cat[c][0])
cat_cards = "".join(
    f'<a class="guidecard" href="/guides/{CATEGORIES[c]["path"]}.html"><img src="/thumbs/{cover(c)["img"]}.jpg" alt="" loading="lazy">'
    f'<span class="gt">{E(CATEGORIES[c]["name"])}</span><span class="gd">{E(CATEGORIES[c]["dates"])} · {len(by_cat[c])} paintings</span></a>'
    for c in CAT_ORDER if by_cat[c])
az = "".join(f'<h3 id="l-{k}">{k}</h3><ul class="az">' + "".join(
    f'<li><a href="/paintings/{p["_slug"]}.html">{E(clean_title(p))}</a> <span>{E(p["artist"])}, {E(p["date"])}</span></li>' for p in ps) + '</ul>'
    for k, ps in letters.items())
artist_list = "".join(f'<li><a href="/artists/{artist_slug[a]}.html">{E(a)}</a></li>' for a in sorted(ARTISTS, key=lambda x: x.split()[-1]) if by_artist.get(a))
body = f'''  <h1>Art guides</h1>
  <p class="lede">Every painting in Out of Focus, with the story behind it, and short guides to the great periods of Western art.</p>
  <p>Out of Focus is a daily art puzzle: each painting starts as a blurry mosaic and sharpens step by step until you can name it. These pages tell you about the {len(P)} paintings in the game: who painted them, when, where you can see them today and why they matter. Read up before you play, or come back after a round to learn about the painting that stumped you.</p>
  <h2>Styles and periods</h2>
  <div class="guides">{cat_cards}</div>
  <h2>Artists</h2>
  <ul class="artists">{artist_list}</ul>
  <h2>All {len(P)} paintings, A to Z</h2>
  {az}'''
urls.insert(0, page("guides/index.html", "Art guides: every painting in Out of Focus", f"Guides to {len(P)} famous paintings and the periods of Western art, from the Renaissance to Post-Impressionism.", body, None, None))

# ---------- sitemap + robots ----------
root = [f"{BASE}/", f"{BASE}/how-to-play.html", f"{BASE}/about.html", f"{BASE}/privacy.html", f"{BASE}/contact.html"]
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
    f"  <url><loc>{u}</loc></url>\n" for u in root + urls) + "</urlset>\n"
open(os.path.join(SITE, "sitemap.xml"), "w").write(sm)
open(os.path.join(SITE, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
print(f"{len(P)} paintings, {len([a for a in ARTISTS if by_artist.get(a)])} artists, {len(urls)} pages")
