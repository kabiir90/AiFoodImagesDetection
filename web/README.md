# Food Scanner — static web build (Vercel / Netlify / GitHub Pages)

This folder is a **fully standalone** version of the app. All AI inference runs in the
browser (TensorFlow.js) and every asset is static — **no server, no Node-RED needed**.

```
web/
├─ index.html          # the whole app (UI + in-browser inference)
└─ food-model/         # model.json + weights, labels.json, calories.json,
                       # tf.min.js, chart.umd.min.js, ph-duotone.css, fonts
```

## Deploy to Vercel — 3 ways

### Option 1 — Vercel CLI (fastest)
```bash
npm i -g vercel
cd web
vercel        # first run: log in + accept defaults
vercel --prod # promote to production
```
When asked for settings, accept the defaults (no build step, output = current dir).

### Option 2 — GitHub + Vercel dashboard
1. Push the project to a GitHub repo.
2. vercel.com → **Add New → Project** → import the repo.
3. **Root Directory:** `web` · **Framework Preset:** Other · **Build Command:** *(empty)* ·
   **Output Directory:** `.`
4. Deploy.

### Option 3 — Drag & drop
vercel.com → new project → drag the `web/` folder onto the dashboard.

## Notes
- The model is ~10 MB (loaded once, then cached) — fine for Vercel/Netlify free tiers.
- **Camera** needs HTTPS — Vercel serves HTTPS automatically, so the live camera works
  online (locally it only worked on `localhost`).
- Works identically on **Netlify** (drag the folder) or **GitHub Pages** (push `web/` to a
  `gh-pages` branch / set Pages source to this folder).
- This static site is independent from the Node-RED workflow (kept for the report's bonus
  part). To refresh the model after retraining: re-run `convert_to_tfjs.py`, then copy
  `node-red/model/*` into `web/food-model/` and redeploy.
