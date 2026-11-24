# Crowd Pilot AI

Early prototype of a crowd-safety tool for festival crowds in Kolkata (pandals, temporary pavilions, road closures).

**Status:** early prototype. The vision core works on a test clip. It has not been validated against ground truth and is **not** a safety tool.

## The idea

Two interconnected interfaces built on one shared data pipeline:

1. **Public Guide (`/public`):** Mobile-first visitor routing that uses live crowd density and gate-to-pandal walking times to suggest less crowded alternatives when an area approaches capacity. Statuses are expressed in calm words (e.g., CLEAR, BUSY, VERY BUSY, CLOSED), never raw headcount numbers.
2. **Authority Dashboard (`/`):** Real-time monitoring for organisers and police on duty. Displays density per zone across a 3×4 grid, alert streaks with actionable recommendations (e.g. limit entry or open diversions), inside-floor occupancy history, and administrative pandal access controls.

Crush risk depends on **density** (people per square metre), not on total headcount, so the pipeline estimates density per zone rather than a single count.

## Architecture

- **`cv-service/` (FastAPI backend):**
  - Runs crowd-density estimation via CSRNet (ShanghaiTech Part A weights via LWCC) on a looping video in a background worker thread.
  - Maintains state for a network of 5 pandals (Pandal A fed by the camera feed; Pandals B–E simulated).
  - Exposes typed REST API endpoints:
    - `GET /api/state` — Full authority telemetry (zones, alerts, history, pandals, advisories).
    - `GET /api/sites` — Public status list (names and status words only, no counts).
    - `GET /api/recommend` — Capacity-aware rerouting based on entry gate and desired pandal.
    - `POST /api/admin/closed` — Protected administrative control to toggle pandal closure.
  - Serves the compiled production React SPA when `frontend/dist` is built, with automatic fallback to lightweight inline HTML if unbuilt.
- **`frontend/` (React application):**
  - Built with React 19, TypeScript, Tailwind CSS v4, and Lucide icons via Vite.
  - Features real-time polling (1s on Authority view, 3s on Public view), stale-data detection (>10s), in-flight request cancellation, and loading/error states.
- **`cv-service/experiments/yolo_baseline.py`:**
  - Documented baseline experiment demonstrating that bounding-box object detection struggles in dense, heavily occluded crowds, validating the density-map approach.

## Findings so far

On one 11-second indoor test clip, the model counted about 350 people per reading, but only about 190 of them were on the hall floor. The rest were a crowd outside the glass doors. Nearly half of everything counted was in the wrong place. Defining _where_ to count matters as much as counting.

## Limitations (please read)

- Tested on **one short clip**. No accuracy validation against hand counts yet.
- The model undercounts large, close-up people (foreground) and can count distant crowds seen through windows.
- Floor areas are **assumptions**. Converting counts to people/m² needs per-camera calibration (planned: ground-plane homography from measured reference points). Until then, the RED/AMBER/GREEN levels are illustrative.
- No real camera feeds. Access to CCTV would need a partnership with the relevant authorities. Only Pandal A uses the camera feed; Pandals B to E are simulated.
- Administrative PIN is demo-only (`1234`), held exclusively in browser memory.

## Run it

Requires Python 3.9+ and Node.js 20+.

### Option A: Two-terminal development mode (recommended for UI development)

**Terminal 1 — Vision & API Service:**
```bash
cd cv-service
source .venv/bin/activate
python server.py
```
API runs at `http://127.0.0.1:8000`.

**Terminal 2 — Frontend Dev Server:**
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173/` for the Authority Dashboard, or `http://localhost:5173/public` for the Public Guide. Requests to `/api/*` are automatically proxied to the backend.

### Option B: Single-server production mode

Build the frontend once, then let FastAPI serve everything:
```bash
# 1. Build the frontend
cd frontend
npm install
npm run build

# 2. Run the server
cd ../cv-service
source .venv/bin/activate
python server.py
```
Open `http://127.0.0.1:8000/` for the Authority view or `http://127.0.0.1:8000/public` for the Public view.

> **Note:** In single-server mode, `frontend/dist` must be rebuilt (`npm run build`) and `python server.py` restarted to see UI changes.

### Running Backend Unit Tests

Unit tests verify the hysteresis threshold logic, alert suggestions, routing algorithm, and admin controls:
```bash
cd cv-service
source .venv/bin/activate
python test_server_logic.py
```

### Known issue: LWCC on macOS

LWCC 0.0.7 tries to save weights to `/.lwcc/weights`, which is read-only on macOS. Patch the installed package once after `pip install`:

```bash
F=.venv/lib/python3.9/site-packages/lwcc/util/functions.py
sed -i '' 's#"/.lwcc/weights"#os.path.expanduser("~/.lwcc/weights")#' $F
sed -i '' 's#"/.lwcc/weights/"#".lwcc/weights/"#' $F
```

## Demo Script

A complete 2-minute walkthrough script covering the authority dashboard, calibration notice, pandal closing, and public rerouting is available in [docs/DEMO.md](docs/DEMO.md).

## Roadmap

- [ ] Floor calibration (homography) to estimate real area per zone
- [ ] Validate counts against manual counts; test on footage of Indian festival crowds
- [x] Hysteresis on alert thresholds (avoid flicker near a boundary)
- [x] Backend API serving zone densities
- [x] Authority dashboard and controls (Close / Reopen pandals)
- [x] Public app with capacity-aware rerouting (avoid sending everyone to the same alternative)

## Data and privacy

No footage is included in this repo. The system estimates density; it does not identify people and does not need faces.

## Licence

Not chosen yet.
