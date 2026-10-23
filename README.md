# Nexis theme previews

Live HTML previews and listing images for the Shopify themes sold on
https://nexissolutions1.com/marketplace. One folder per theme code
(`nx-theme-001/`): `index.html`, `img/` (Unsplash photos, see `img/CREDITS.md`),
`cover.jpg`, `mockup.jpg` and `shots/`.

Photos: `.github/workflows/photos.yml` runs `tools/photos.py` on GitHub Actions
(search makes contact sheets in `<code>/_sheets/`, fetch downloads the picks
listed in `jobs/<code>.json`).

Demo photos are for preview only and are not included in the theme files.
