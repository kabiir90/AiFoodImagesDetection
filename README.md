# 🍽️ Food Calorie Scanner — Node-RED + TensorFlow.js

Point a camera at a dish → the app recognizes it (1 of 101 foods) → estimates
calories → shows it in a clean Node-RED dashboard. The AI model is trained on the
**Food-101** dataset and runs **in the browser** (TensorFlow.js), so the deployment
laptop only needs Node-RED — no Python at runtime.

```
Camera / Upload  →  Food classification (MobileNetV2, in-browser TF.js)  →  Calorie lookup  →  Dashboard UI
```

## Pipeline note (read this)
- **Food-101 is a classification dataset** (one centered dish per image, no bounding
  boxes). So v1 classifies the **whole frame** — perfect for "point at your plate".
- **True multi-item detection** (boxes around several foods) needs an extra detector
  (e.g. YOLO) — that's the v2 upgrade path, not Food-101 alone.
- Calories are **not** in Food-101; they live in [data/calories.json](data/calories.json)
  (kcal per typical serving for all 101 classes — tune these to your needs).

## Project layout
```
NodeRedApp/
├─ data/
│  └─ calories.json          # 101 foods → kcal + serving size
├─ training/                 # runs on THIS laptop (Python 3)
│  ├─ requirements.txt
│  ├─ train.py               # transfer learning on Food-101 (MobileNetV2)
│  └─ convert_to_tfjs.py     # Keras → TensorFlow.js
├─ node-red/                 # runs on the OTHER laptop
│  ├─ flow.json              # importable dashboard + AI flow
│  ├─ ui_template.html       # source of the dashboard UI (already inside flow.json)
│  └─ model/                 # created by convert step (model.json + weights)
├─ docs/
│  └─ DEPLOY.md              # step-by-step deploy on the other laptop
└─ food-101/                 # the dataset (101 classes, 101,000 images)
```

## How to build it (3 steps)

### 1️⃣ Train the model (this laptop, has GPU = much faster)
```powershell
cd training
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python train.py --data ../food-101/food-101 --epochs 15
```
Outputs `training/artifacts/food101_mobilenetv2.keras` + `labels.json`.
> No GPU? It still trains on CPU but slowly. You can lower `--epochs` to test the
> end-to-end pipeline first, then train properly later.

### 2️⃣ Convert to TensorFlow.js
```powershell
python convert_to_tfjs.py
copy ..\data\calories.json ..\node-red\model\
```
This fills `node-red/model/` with `model.json`, weight shards, `labels.json`, `calories.json`.

### 3️⃣ Deploy on the other laptop
Copy `node-red/flow.json` + the whole `node-red/model/` folder over, then follow
**[docs/DEPLOY.md](docs/DEPLOY.md)** (install Node-RED + dashboard, serve the model
folder statically, import the flow, open `/ui`).

## Dataset status ✅
Food-101 verified intact: **101 classes × 1,000 images = 101,000**, official
75,750 / 25,250 train/test split, all meta files present.
`archive.zip` (10 GB) is just the original download — safe to delete after the
extracted `food-101/` is confirmed working.

## Roadmap to "professional"
1. **Accuracy** — train full 15+ epochs with fine-tuning; expect ~80%+ top-1 on
   Food-101 with MobileNetV2 (higher with EfficientNet, at a size cost).
2. **Portion/weight estimation** — calories currently assume a standard serving.
   Add a reference object or depth estimate to scale by real portion size.
3. **Multi-food detection (v2)** — add a YOLO detector to box multiple items, then
   classify each crop with this model.
4. **History & goals** — store scans (already logged to `food_scans.log`) in a DB
   (SQLite/Influx), add daily-total and charts on the dashboard.
5. **Confidence gating** — if top-1 confidence < threshold, ask the user to confirm
   or re-shoot, instead of guessing.
6. **Packaging** — ship Node-RED + flow as a single installer or Docker image for
   one-click deploy on any laptop.
