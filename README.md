# Crowd Pilot AI

Early prototype of a crowd-safety tool for festival crowds in Kolkata (pandals, temporary pavilions, road closures).

**Status:** early prototype. The vision core works on a test clip. It has not been validated against ground truth and is **not** a safety tool.

## The idea

Two apps built on one shared data pipeline:

1. **Public app:** uses live crowd density and road-closure data to suggest less crowded routes, or a different pavilion, when an area is getting dense.
2. **Authority dashboard:** for organisers and police on duty. Live density per zone, warnings when an area stays too crowded, and suggested actions (for example, pause entry at a gate).

Crush risk depends on **density** (people per square metre), not on total headcount, so the pipeline estimates density per zone rather than a single count.

## What works today (`cv-service/`)

- Crowd counting from video using a pretrained CSRNet model (ShanghaiTech Part A weights, via the [LWCC](https://pypi.org/project/lwcc/) package).
- Per-zone counts on a grid, smoothed over the last 3 readings.
- Alert rule: a zone must stay RED for 3 readings in a row before an alert fires.
- Plausibility check: densities above 8 people/m² are flagged `CHECK` (the area assumption must be wrong), not treated as an emergency.
- Floor outline: you click the walkable floor in the camera view, and only people inside it are counted.
- Script to render presentation images (heatmap, per-zone counts, before/after).

`backend/` and `frontend/` hold early scaffolding for the planned dashboard and are not yet connected to the vision code.

## Findings so far

On one 11-second indoor test clip, the model counted about 350 people per reading, but only about 190 of them were on the hall floor. The rest were a crowd outside the glass doors. Nearly half of everything counted was in the wrong place. Defining _where_ to count matters as much as counting.

## Limitations (please read)

- Tested on **one short clip**. No accuracy validation against hand counts yet.
- The model undercounts large, close-up people (foreground) and can count distant crowds seen through windows.
- Floor areas are **assumptions**. Converting counts to people/m² needs per-camera calibration (planned: ground-plane homography from measured reference points). Until then, the RED/AMBER/GREEN levels are not meaningful.
- No real camera feeds. Access to CCTV would need a partnership with the relevant authorities.

## Run it

Requires Python 3.9+.

```bash
cd cv-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# put a crowd video at cv-service/crowd_video.mp4 (not included in this repo)
python pick_points.py      # click the floor outline, press q
python video_roi.py        # counts everyone vs people inside the floor
python video_zones_v2.py   # zone densities, smoothing, alerts
python make_visuals.py     # presentation images in cv-service/visuals/
```

Edit the `POINTS` list in `video_roi.py` and `make_visuals.py` with the points printed by `pick_points.py`.

### Known issue: LWCC on macOS

LWCC 0.0.7 tries to save weights to `/.lwcc/weights`, which is read-only on macOS. Patch the installed package once after `pip install`:

```bash
F=.venv/lib/python3.9/site-packages/lwcc/util/functions.py
sed -i '' 's#"/.lwcc/weights"#os.path.expanduser("~/.lwcc/weights")#' $F
sed -i '' 's#"/.lwcc/weights/"#".lwcc/weights/"#' $F
```

(Adjust `python3.9` to your Python version. Reinstalling LWCC removes the patch.)

## Roadmap

- [ ] Floor calibration (homography) to estimate real area per zone
- [ ] Validate counts against manual counts; test on footage of Indian festival crowds
- [ ] Hysteresis on alert thresholds (avoid flicker near a boundary)
- [ ] Backend API serving zone densities
- [ ] Authority dashboard
- [ ] Public app with capacity-aware rerouting (avoid sending everyone to the same alternative)

## Data and privacy

No footage is included in this repo. The system estimates density; it does not identify people and does not need faces.

## Licence

Not chosen yet.
