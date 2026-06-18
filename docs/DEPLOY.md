# Deploying the Food Calorie Scanner on the other laptop (Node-RED)

The other laptop only needs **Node.js + Node-RED**. Python is NOT needed there —
the AI model runs in the browser via TensorFlow.js. You bring two things from
your training laptop: the **flow.json** and the **model folder**.

## What to copy to the other laptop
```
node-red/flow.json              <- the dashboard + AI flow
node-red/model/                 <- model.json, group1-shard*.bin, labels.json, calories.json
```
Put the `model/` folder somewhere stable, e.g. `C:\food\model\`.
(Remember to copy `data/calories.json` INTO that model folder — the UI fetches
`food-model/calories.json`.)

## 1. Install Node-RED (once)
```powershell
npm install -g --unsafe-perm node-red
node-red
```
Open http://localhost:1880 (editor) — the dashboard will be at /ui.

## 2. Install the dashboard nodes
In the editor: **menu ☰ → Manage palette → Install** →
search and install **node-red-dashboard**. Restart if prompted.

## 3. Serve the model folder as static files
Node-RED must serve `model/` at the path `/food-model/`.
Edit the Node-RED settings file (usually `~/.node-red/settings.js`), set:
```js
httpStatic: [
  { path: "C:/food/model", root: "/food-model/" }
],
```
Restart Node-RED. Verify in a browser: http://localhost:1880/food-model/model.json
should return JSON (not 404).

> CORS note: serving from the same Node-RED origin avoids CORS issues entirely.
> Keep the model on the same machine/origin as the dashboard.

## 4. Import the flow
Editor → **menu ☰ → Import** → select `node-red/flow.json` → **Import** → **Deploy**.

## 5. Use it
Open **http://localhost:1880/ui** → tab **Food Scanner**.
- Click **Start camera**, point at a dish, click **Scan food**, or
- Click **Upload photo**.
You'll see the food name, calories, confidence, and top alternatives.
Every scan is logged to `food_scans.log` and shown in the debug sidebar.

## Access from a phone on the same Wi-Fi
Find the laptop IP (`ipconfig`), then open `http://<laptop-ip>:1880/ui` on the phone.
Camera access over plain HTTP works on `localhost` but phones may require HTTPS —
either use the upload button, or put Node-RED behind HTTPS (self-signed cert in
`settings.js`, or a reverse proxy like Caddy).

## Troubleshooting
| Symptom | Fix |
|---|---|
| "Could not load model" | Check `/food-model/model.json` opens in browser; fix `httpStatic`. |
| Camera blocked | Allow camera permission; on phone use HTTPS or the upload button. |
| Wrong/odd predictions | Model still training or low epochs — retrain longer (see training/). |
| Calories show "?" | `calories.json` missing from the model folder. |
