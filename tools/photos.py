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


def search(q, orientation=None, per_page=30):
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
            (out / f"{name}.json").write_text(json.dumps([{k: it[k] for k in ("id", "desc", "w", "h", "author", "link")} for it in items], indent=1))
            sheet(items, out / f"{name}.jpg")
            print(f"{q['q']}: {len(items)} free results")
    elif mode == "fetch":
        out = ROOT / code / "img"
        out.mkdir(parents=True, exist_ok=True)
        credits = ["# Photo credits", "", "All photos from Unsplash under the free Unsplash License (https://unsplash.com/license).", ""]
        for p in job.get("pick", []):
            info = requests.get(f"https://unsplash.com/napi/photos/{p['id']}", headers=UA, timeout=30).json()
            if info.get("premium") or info.get("plus"):
                print("skipping premium photo", p["id"])
                continue
            w = p.get("w", 1600)
            raw = info["urls"]["raw"]
            url = f"{raw}&w={w}&q=82&fm=jpg" + (f"&h={p['h']}&fit=crop" if p.get("h") else "")
            im = Image.open(io.BytesIO(requests.get(url, timeout=60).content)).convert("RGB")
            im.save(out / f"{p['name']}.webp", "WEBP", quality=p.get("quality", 78))
            credits.append(f"- {p['name']}.webp: photo {p['id']} by {info['user']['name']}, {info['links']['html']}")
            print("saved", p["name"], im.size)
        (out / "CREDITS.md").write_text("\n".join(credits) + "\n")
    else:
        sys.exit("mode must be search or fetch")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
