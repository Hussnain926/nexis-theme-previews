#!/usr/bin/env python3
"""Photos for a theme design, from Unsplash (free Unsplash License only).

Runs on GitHub Actions, which can reach Unsplash.

  search: python tools/photos.py search jobs/<code>.json
      For each query in the job, saves the first free results as a numbered
      contact sheet (<code>/_sheets/<query-slug>.jpg) and <code>/_sheets/<query-slug>.json.
  fetch:  python tools/photos.py fetch jobs/<code>.json
      Downloads every {"name", "id"} in "pick" to <code>/img/<name>.webp
      (width "w", default 1600) and writes <code>/img/CREDITS.md.

Job file: {"code": "nx-theme-001",
           "queries": [{"q": "gold necklace model", "orientation": "portrait"}],
           "pick": [{"name": "hero", "id": "abc123", "w": 1800}]}
"""
import io, json, re, sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept": "application/json"}
ROOT = Path(__file__).resolve().parent.parent


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


PEXELS_KEY = __import__("os").environ.get("PEXELS_API_KEY", "")


def search_pexels(q, orientation=None, per_page=30):
    params = {"query": q, "per_page": per_page}
    if orientation:
        params["orientation"] = {"squarish": "square"}.get(orientation, orientation)
    r = requests.get("https://api.pexels.com/v1/search", params=params, headers={"Authorization": PEXELS_KEY}, timeout=30)
    r.raise_for_status()
    return [{
        "id": f"pexels-{p['id']}", "desc": p.get("alt") or "", "w": p["width"], "h": p["height"],
        "raw": p["src"]["original"], "thumb": p["src"]["medium"], "author": p["photographer"], "link": p["url"],
        "license": "Pexels License",
    } for p in r.json().get("photos", [])]


def search_openverse(q, orientation=None, per_page=30):
    params = {"q": q, "page_size": per_page, "license_type": "commercial,modification", "mature": "false"}
    if orientation in ("landscape", "portrait"):
        params["aspect_ratio"] = {"landscape": "wide", "portrait": "tall"}[orientation]
    elif orientation == "squarish":
        params["aspect_ratio"] = "square"
    r = requests.get("https://api.openverse.org/v1/images/", params=params, headers=UA, timeout=30)
    r.raise_for_status()
    out = []
    for p in r.json().get("results", []):
        if (p.get("width") or 0) < 1200:
            continue
        out.append({
            "id": f"ov-{p['id']}", "desc": p.get("title") or "", "w": p.get("width"), "h": p.get("height"),
            "raw": p["url"], "thumb": p.get("thumbnail") or p["url"], "author": p.get("creator") or "unknown",
            "link": p.get("foreign_landing_url") or p["url"], "license": f"CC {p.get('license','').upper()} {p.get('license_version') or ''}".strip(),
        })
    return out


def search(q, orientation=None, per_page=30):
    if PEXELS_KEY:
        return search_pexels(q, orientation, per_page)
    try:
        return search_unsplash(q, orientation, per_page)
    except requests.HTTPError:
        return search_openverse(q, orientation, per_page)


def search_unsplash(q, orientation=None, per_page=30):
    params = {"query": q, "per_page": per_page}
    if orientation:
        params["orientation"] = orientation
    r = requests.get("https://unsplash.com/napi/search/photos", params=params, headers=UA, timeout=30)
    r.raise_for_status()
    out = []
    for p in r.json().get("results", []):
        if p.get("premium") or p.get("plus"):
            continue
        out.append({
            "id": p["id"],
            "desc": p.get("alt_description") or p.get("description") or "",
            "w": p["width"], "h": p["height"],
            "raw": p["urls"]["raw"],
            "thumb": p["urls"]["small"],
            "author": p["user"]["name"],
            "link": p["links"]["html"],
            "license": "Unsplash License",
        })
    return out


def sheet(items, path):
    cols, tw, th = 4, 300, 300
    rows = (len(items) + cols - 1) // cols
    img = Image.new("RGB", (cols * tw, rows * th), "white")
    d = ImageDraw.Draw(img)
    for i, it in enumerate(items):
        try:
            t = Image.open(io.BytesIO(requests.get(it["thumb"], timeout=30).content)).convert("RGB")
            t.thumbnail((tw - 8, th - 8))
            x, y = (i % cols) * tw, (i // cols) * th
            img.paste(t, (x + 4, y + 4))
            d.rectangle([x + 4, y + 4, x + 40, y + 30], fill="black")
            d.text((x + 10, y + 10), str(i), fill="white")
        except Exception as e:  # noqa
            print("thumb failed", it["id"], e)
    img.save(path, quality=80)


def main(mode, job_path):
    job = json.loads(Path(job_path).read_text())
    code = job["code"]
    if mode == "search":
        out = ROOT / code / "_sheets"
        out.mkdir(parents=True, exist_ok=True)
        for q in job.get("queries", []):
            items = search(q["q"], q.get("orientation"))[: q.get("n", 16)]
            name = slug(q["q"] + "-" + (q.get("orientation") or "any"))
            (out / f"{name}.json").write_text(json.dumps([{k: it.get(k) for k in ("id", "desc", "w", "h", "author", "link", "raw", "license")} for it in items], indent=1))
            sheet(items, out / f"{name}.jpg")
            print(f"{q['q']}: {len(items)} free results")
    elif mode == "fetch":
        out = ROOT / code / "img"
        out.mkdir(parents=True, exist_ok=True)
        credits = ["# Photo credits", "", "Demo photos for preview only; not included in the theme files.", ""]
        known = {}
        for f in (ROOT / code / "_sheets").glob("*.json"):
            for it in json.loads(f.read_text()):
                known[it["id"]] = it
        for p in job.get("pick", []):
            w = p.get("w", 1600)
            if p.get("url"):
                it = {"raw": p["url"], "author": p.get("author", "Canva"), "link": p.get("link", ""), "license": p.get("license", "Generated with Canva")}
            elif p["id"] in known:
                it = known[p["id"]]
            else:
                print("unknown photo id, run search first:", p["id"])
                continue
            im = Image.open(io.BytesIO(requests.get(it["raw"], headers=UA, timeout=90).content)).convert("RGB")
            if im.width > w:
                im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
            if p.get("crop"):  # "4:5" style centre crop
                a, b = (int(x) for x in p["crop"].split(":"))
                tw, th = im.width, round(im.width * b / a)
                if th > im.height:
                    th, tw = im.height, round(im.height * a / b)
                l, t = (im.width - tw) // 2, (im.height - th) // 2
                im = im.crop((l, t, l + tw, t + th))
            im.save(out / f"{p['name']}.webp", "WEBP", quality=p.get("quality", 78))
            credits.append(f"- {p['name']}.webp: {it.get('author')}, {it.get('license', '')}, {it.get('link')}")
            print("saved", p["name"], im.size)
        (out / "CREDITS.md").write_text("\n".join(credits) + "\n")
    else:
        sys.exit("mode must be search or fetch")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
