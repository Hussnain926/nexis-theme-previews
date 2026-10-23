// Listing images for one theme design: full-page shots of all 10 pages (cut into
// parts of at most 2400 px), cover.jpg (1440x900 home top), mockup.jpg (laptop +
// phone on the palette background) and mobile.jpg (three phone screens).
//   node tools/shots.mjs nx-theme-001 "#F4EFE9" "#12403C"
// Needs Playwright (PLAYWRIGHT_PATH points at its index.mjs when not installed locally).
import path from "node:path";
import { mkdirSync, rmSync } from "node:fs";

const { chromium } = await import(process.env.PLAYWRIGHT_PATH || "playwright");
const [code, bg = "#F4EFE9", accent = "#12403C"] = process.argv.slice(2);
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const dir = path.join(root, code);
const file = "file://" + path.join(dir, "index.html");
const shots = path.join(dir, "shots");
rmSync(shots, { recursive: true, force: true });
mkdirSync(shots, { recursive: true });
const PAGES = ["home", "collection", "product", "cart", "search", "blog", "article", "about", "contact", "404"];

const b = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
async function open(w, h, page) {
  const p = await b.newPage({ viewport: { width: w, height: h } });
  await p.goto(file, { waitUntil: "load" });
  await p.evaluate(() => document.fonts.ready);
  await p.evaluate((pg) => {
    window.go(pg);
    document.querySelector(".dz")?.remove();
    document.querySelectorAll(".reveal").forEach((r) => r.classList.add("in"));
    document.querySelector(".sticky-atc")?.remove();
  }, page);
  await p.waitForTimeout(700);
  return p;
}

// 1. full-page desktop shots, cut into parts
for (const pg of PAGES) {
  const p = await open(1440, 900, pg);
  const h = await p.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0, n = 1; y < h; y += 2400, n++) {
    await p.screenshot({ path: path.join(shots, `p-full-${pg}-${n}.jpg`), type: "jpeg", quality: 82, clip: { x: 0, y, width: 1440, height: Math.min(2400, h - y) }, fullPage: true });
  }
  await p.close();
}

// 2. cover + phone screens as data URLs for the composites
const shot = async (w, h, pg, scrollY = 0) => {
  const p = await open(w, h, pg);
  if (scrollY) await p.evaluate((y) => window.scrollTo(0, y), scrollY);
  await p.waitForTimeout(300);
  const buf = await p.screenshot({ type: "jpeg", quality: 88 });
  await p.close();
  return "data:image/jpeg;base64," + buf.toString("base64");
};
const cover = await shot(1440, 900, "home");
const pHome = await shot(390, 844, "home");
const pProduct = await shot(390, 844, "product");
const pCollection = await shot(390, 844, "collection", 380);
const c = await b.newPage({ viewport: { width: 1440, height: 900 } });
await c.setContent(`<img src="${cover}" style="display:block;width:1440px;height:900px">`);
await c.screenshot({ path: path.join(dir, "cover.jpg"), type: "jpeg", quality: 86 });

const phone = (src, extra = "") => `<div style="width:300px;height:640px;border-radius:46px;padding:11px;background:linear-gradient(145deg,#3a3d3b,#0c0d0c 40%,#1f2120);box-shadow:0 60px 100px -40px rgba(0,0,0,.6);${extra}"><div style="width:100%;height:100%;border-radius:36px;overflow:hidden;background:#fff"><img src="${src}" style="width:100%;display:block"></div></div>`;
await c.setViewportSize({ width: 1600, height: 1000 });
await c.setContent(`<body style="margin:0;width:1600px;height:1000px;background:radial-gradient(80% 80% at 30% 20%,#fff 0%,${bg} 55%,${bg} 100%);position:relative;overflow:hidden;font-family:sans-serif">
  <div style="position:absolute;left:110px;top:120px;width:1120px">
    <div style="background:#1b1b1b;border-radius:22px 22px 0 0;padding:22px 22px 0"><div style="height:660px;overflow:hidden;border-radius:6px 6px 0 0;background:#fff"><img src="${cover}" style="width:100%;display:block"></div></div>
    <div style="height:26px;background:linear-gradient(#d9d9d9,#a9a9a9);border-radius:0 0 26px 26px;margin:0 -60px"></div>
  </div>
  <div style="position:absolute;right:120px;top:240px">${phone(pProduct)}</div>
  <div style="position:absolute;left:0;right:0;bottom:0;height:10px;background:${accent}"></div>
</body>`);
await c.screenshot({ path: path.join(dir, "mockup.jpg"), type: "jpeg", quality: 86 });

await c.setViewportSize({ width: 1600, height: 1000 });
await c.setContent(`<body style="margin:0;width:1600px;height:1000px;background:${accent};display:flex;gap:70px;justify-content:center;align-items:center">
  ${phone(pHome, "transform:translateY(30px)")}${phone(pProduct, "transform:translateY(-30px)")}${phone(pCollection, "transform:translateY(30px)")}
</body>`);
await c.screenshot({ path: path.join(dir, "mobile.jpg"), type: "jpeg", quality: 86 });
await b.close();
console.log("shots, cover.jpg, mockup.jpg and mobile.jpg written in", dir);
