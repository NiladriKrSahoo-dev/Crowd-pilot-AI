import hmac
import math
import os
import random
import threading
import time
from collections import deque

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from lwcc import LWCC

# ---------------- settings ----------------
VIDEO = "crowd_video.mp4"
ROWS = 3
COLS = 4
POINTS = [(108, 254), (1266, 300), (2284, 342), (2296, 1058),
          (1144, 1068), (24, 1060), (8, 330)]
ROW_AREA_M2 = [30.0, 15.0, 6.0]   # ASSUMPTION: replace with measured areas
CALIBRATED = False                # becomes True once areas come from a measurement
SAMPLE_EVERY_SEC = 1
SMOOTH_N = 3
ALERT_AFTER = 3
MAX_PLAUSIBLE = 8.0

# Demo pandals. Only A is fed by the camera. The others are simulated.
# Capacities and walking times are made up for the demo.
SITES = {
    "A": {"name": "Pandal A", "capacity": 260, "live": True, "closed": False},
    "B": {"name": "Pandal B", "capacity": 180, "closed": False},
    "C": {"name": "Pandal C", "capacity": 300, "closed": False},
    "D": {"name": "Pandal D", "capacity": 220, "closed": False},
    "E": {"name": "Pandal E", "capacity": 150, "closed": False},
}
# Demo-only administrative PIN. In production this would be backed by an auth provider.
ADMIN_PIN = "1234"
WALK_MIN = {
    "North gate": {"A": 4, "B": 7, "C": 12, "D": 9, "E": 15},
    "East gate": {"A": 9, "B": 3, "C": 6, "D": 10, "E": 8},
    "South gate": {"A": 12, "B": 8, "C": 4, "D": 5, "E": 6},
}
BUSY_AT = 0.60
VERY_BUSY_AT = 0.85
REDIRECT_WEIGHT = 8     # ASSUMPTION: one recommendation stands for a group of about 8 people
PENDING_DECAY = 0.9     # expected arrivals fade by 10% every second
# ------------------------------------------

lock = threading.Lock()
state = {
    "ready": False,
    "calibrated": CALIBRATED,
    "video_time": 0,
    "clock": "",
    "everyone": 0,
    "inside": 0,
    "zones": [],
    "alerts": [],
    "history": [],
    "sites": [],
    "advisories": [],
}
alerts = deque(maxlen=30)
history = deque(maxlen=60)
advisories = deque(maxlen=15)
no_room_events = deque()
last_no_room_alert_time = 0.0
loads = {sid: 0.5 * cfg["capacity"] for sid, cfg in SITES.items()}
pending = {sid: 0.0 for sid in SITES}


# ---------- crowd levels (authority side) ----------
def next_level(prev, density):
    # Thresholds go up at 2 and 4 people/m2, but come back down a little lower
    # (1.8 and 3.6) so a reading hovering near a line does not flicker.
    if density > MAX_PLAUSIBLE:
        return "CHECK"
    if prev == "RED":
        if density >= 3.6:
            return "RED"
        return "AMBER" if density >= 1.8 else "GREEN"
    if prev == "AMBER":
        if density >= 4.0:
            return "RED"
        return "AMBER" if density >= 1.8 else "GREEN"
    if density >= 4.0:
        return "RED"
    if density >= 2.0:
        return "AMBER"
    return "GREEN"


def suggested_action(level, zone_id):
    if level == "RED":
        return f"Z{zone_id}: limit new entry nearby and open a diversion"
    if level == "AMBER":
        return f"Z{zone_id}: keep watching and get a diversion ready"
    if level == "CHECK":
        return f"Z{zone_id}: density is impossible, check the zone area"
    return ""


# ---------- pandals and rerouting (public side) ----------
# The functions below must be called while holding `lock`.
def occupancy(site_id):
    # People there now PLUS people we have recently sent there.
    effective = loads[site_id] + REDIRECT_WEIGHT * pending[site_id]
    return effective / SITES[site_id]["capacity"]


def status_for(occ):
    if occ >= VERY_BUSY_AT:
        return "VERY BUSY"
    if occ >= BUSY_AT:
        return "BUSY"
    return "CLEAR"


def publish_sites():
    rows = []
    for sid, cfg in SITES.items():
        occ = occupancy(sid)
        is_closed = bool(cfg.get("closed", False))
        rows.append({
            "id": sid,
            "name": cfg["name"],
            "live": bool(cfg.get("live")),
            "closed": is_closed,
            "people": round(loads[sid]),
            "capacity": cfg["capacity"],
            "occupancy": round(occ * 100),
            "status": "CLOSED" if is_closed else status_for(occ),
        })
    state["sites"] = rows
    state["advisories"] = list(advisories)
    state["alerts"] = list(alerts)


def recommend(gate, want):
    minutes = WALK_MIN[gate]
    want_name = SITES[want]["name"]
    occ_want = occupancy(want)
    dest = None
    redirected = False

    want_closed = bool(SITES[want].get("closed", False))

    if not want_closed and occ_want < VERY_BUSY_AT:
        dest = want
        if occ_want < BUSY_AT:
            message = (f"{want_name} has plenty of room right now. "
                       f"About {minutes[want]} minutes from the {gate}.")
        else:
            message = (f"{want_name} is busy but moving. About {minutes[want]} minutes "
                       f"from the {gate}. Expect slower walking near the entrance.")
    else:
        options = [s for s in SITES if s != want and not SITES[s].get("closed") and occupancy(s) < VERY_BUSY_AT]
        if options:
            # Prefer a short walk AND a quiet place.
            dest = min(options, key=lambda s: minutes[s] + 20 * occupancy(s))
            redirected = True
            dest_name = SITES[dest]["name"]
            if want_closed:
                message = (f"{want_name} is currently closed. {dest_name} is about "
                           f"{minutes[dest]} minutes from the {gate} and has more room.")
            else:
                message = (f"{want_name} is very busy right now. {dest_name} is about "
                           f"{minutes[dest]} minutes from the {gate} and has more room.")
        else:
            dest = None
            if want_closed:
                message = (f"{want_name} is currently closed and all other pandals are busy. "
                           "Waiting a little before visiting may help.")
            else:
                message = ("All pandals are busy right now. Waiting a little before "
                           "going in may help.")

            now = time.time()
            no_room_events.append(now)
            cutoff = now - 60.0
            while no_room_events and no_room_events[0] < cutoff:
                no_room_events.popleft()

            global last_no_room_alert_time
            if len(no_room_events) >= 5 and (now - last_no_room_alert_time >= 60.0):
                last_no_room_alert_time = now
                n_visitors = len(no_room_events)
                alerts.appendleft({
                    "clock": time.strftime("%H:%M:%S"),
                    "zone": None,
                    "level": "PUBLIC",
                    "message": f"{n_visitors} visitors in the last minute could not be redirected: no open pandal has room",
                    "action": "Consider opening extra capacity or pausing entry at the gates",
                })

    status = "CLOSED" if dest and SITES[dest].get("closed") else (status_for(occupancy(dest)) if dest else None)
    if dest:
        pending[dest] += 1   # remember that we just sent someone there

    advisories.appendleft({
        "clock": time.strftime("%H:%M:%S"),
        "gate": gate,
        "want": want_name,
        "send": SITES[dest]["name"] if dest else "none",
        "redirected": redirected,
    })
    return {
        "send": dest,
        "send_name": SITES[dest]["name"] if dest else None,
        "redirected": redirected,
        "status": status,
        "minutes": minutes[dest] if dest else None,
        "message": message,
    }


# ---------- background jobs ----------
def sim_worker():
    # Moves the simulated pandals up and down so the demo has something to react to.
    rng = random.Random(7)
    phase = {"B": 0.0, "C": 1.5, "D": 3.0, "E": 4.5}
    t = 0
    while True:
        time.sleep(1)
        t += 1
        with lock:
            for sid, cfg in SITES.items():
                if cfg.get("live"):
                    pending[sid] *= PENDING_DECAY
                    continue
                cap = cfg["capacity"]
                target = cap * (0.55 + 0.4 * math.sin(t / 40 + phase[sid]))
                loads[sid] += (target - loads[sid]) * 0.1 + rng.uniform(-0.03, 0.03) * cap
                loads[sid] = max(0.0, min(loads[sid], 1.1 * cap))
                pending[sid] *= PENDING_DECAY
            publish_sites()


def worker():
    model = LWCC.load_model(model_name="CSRNet", model_weights="SHA")

    cap = cv2.VideoCapture(VIDEO)
    if not cap.isOpened():
        print("Could not open", VIDEO)
        return
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    step = int(fps * SAMPLE_EVERY_SEC)

    mask = None
    memory = [[deque(maxlen=SMOOTH_N) for _ in range(COLS)] for _ in range(ROWS)]
    everyone_mem = deque(maxlen=SMOOTH_N)
    inside_mem = deque(maxlen=SMOOTH_N)
    streak = np.zeros((ROWS, COLS), dtype=int)
    level_now = [["GREEN"] * COLS for _ in range(ROWS)]

    frame_no = 0
    just_restarted = False
    while True:
        ok, frame = cap.read()
        if not ok:
            if just_restarted:
                print("Cannot read frames from", VIDEO)
                return
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            frame_no = 0
            just_restarted = True
            continue
        just_restarted = False

        if frame_no % step == 0:
            cv2.imwrite("frame_tmp.jpg", frame)
            _, dm = LWCC.get_count("frame_tmp.jpg", model=model,
                                   return_density=True)
            dm = np.clip(np.squeeze(dm), 0, None)
            h, w = dm.shape

            if mask is None:
                poly = np.array([[x * w / fw, y * h / fh] for x, y in POINTS],
                                dtype=np.int32)
                mask = np.zeros((h, w), dtype=np.uint8)
                cv2.fillPoly(mask, [poly], 1)

            everyone_mem.append(float(dm.sum()))
            inside_mem.append(float((dm * mask).sum()))
            everyone = sum(everyone_mem) / len(everyone_mem)
            inside = sum(inside_mem) / len(inside_mem)
            video_time = int(frame_no / fps)
            clock = time.strftime("%H:%M:%S")

            zone_h = h // ROWS
            zone_w = w // COLS
            zones = []
            for r in range(ROWS):
                for c in range(COLS):
                    y1 = r * zone_h
                    x1 = c * zone_w
                    y2 = h if r == ROWS - 1 else y1 + zone_h
                    x2 = w if c == COLS - 1 else x1 + zone_w
                    count = float((dm[y1:y2, x1:x2] * mask[y1:y2, x1:x2]).sum())

                    memory[r][c].append(count)
                    smooth = sum(memory[r][c]) / len(memory[r][c])
                    density = smooth / ROW_AREA_M2[r]

                    previous = level_now[r][c]
                    level = next_level(previous, density)
                    level_now[r][c] = level

                    if level == "RED":
                        streak[r, c] += 1
                    else:
                        streak[r, c] = 0

                    zone_id = r * COLS + c + 1
                    if streak[r, c] == ALERT_AFTER:
                        alerts.appendleft({
                            "clock": clock,
                            "zone": zone_id,
                            "level": "RED",
                            "message": f"Z{zone_id} has been RED for {ALERT_AFTER} readings in a row",
                            "action": suggested_action("RED", zone_id),
                        })
                    if level == "CHECK" and previous != "CHECK":
                        alerts.appendleft({
                            "clock": clock,
                            "zone": zone_id,
                            "level": "CHECK",
                            "message": f"Z{zone_id} shows {density:.1f} people/m2, which is not possible",
                            "action": suggested_action("CHECK", zone_id),
                        })

                    zones.append({
                        "id": zone_id,
                        "count": round(smooth, 1),
                        "density": round(density, 2),
                        "level": level,
                    })

            history.append(round(inside))
            with lock:
                state["ready"] = True
                state["video_time"] = video_time
                state["clock"] = clock
                state["everyone"] = round(everyone)
                state["inside"] = round(inside)
                state["zones"] = zones
                state["alerts"] = list(alerts)
                state["history"] = list(history)
                loads["A"] = inside          # the camera feeds Pandal A
                publish_sites()

            time.sleep(0.5)

        frame_no += 1


# ---------- web server ----------
app = FastAPI()


@app.get("/api/state")
def get_state():
    with lock:
        return dict(state)


@app.get("/api/sites")
def public_sites():
    # What the public is allowed to see: names and simple statuses, no counts.
    with lock:
        return {
            "gates": list(WALK_MIN.keys()),
            "sites": [{"id": r["id"], "name": r["name"], "status": r["status"]}
                      for r in state["sites"]],
        }


@app.get("/api/recommend")
def api_recommend(gate: str, want: str):
    if gate not in WALK_MIN or want not in SITES:
        raise HTTPException(status_code=400, detail="unknown gate or pandal")
    with lock:
        result = recommend(gate, want)
        publish_sites()
    return result


class AdminClosedRequest(BaseModel):
    site: str
    closed: bool
    pin: str


@app.post("/api/admin/closed")
def admin_closed(payload: AdminClosedRequest):
    if not hmac.compare_digest(payload.pin, ADMIN_PIN):
        raise HTTPException(status_code=403, detail="wrong PIN")
    if payload.site not in SITES:
        raise HTTPException(status_code=400, detail="unknown site")
    with lock:
        SITES[payload.site]["closed"] = payload.closed
        site_name = SITES[payload.site]["name"]
        if payload.closed:
            msg = f"{site_name} closed by the authority"
            act = f"Public guide will redirect visitors away from {site_name} to open alternatives"
        else:
            msg = f"{site_name} reopened"
            act = f"Public guide will include {site_name} in route recommendations"

        alerts.appendleft({
            "clock": time.strftime("%H:%M:%S"),
            "zone": None,
            "level": "ADMIN",
            "message": msg,
            "action": act,
        })
        publish_sites()
    return {"site": payload.site, "closed": payload.closed}


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Crowd Pilot AI - authority view</title>
<style>
  :root {
    --bg: #f5f6f8; --card: #ffffff; --text: #1b1f24; --muted: #667085;
    --line: #dfe3e8;
    --green: #d7f0dc; --green-t: #14532d;
    --amber: #fde8c0; --amber-t: #7a4a00;
    --red: #f9d0d0; --red-t: #8a1111;
    --check: #e3e5ea; --check-t: #3b4252;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #12151a; --card: #1b2028; --text: #eceff4; --muted: #98a2b3;
      --line: #2c3340;
      --green: #1d4a2b; --green-t: #c7f0d2;
      --amber: #5a4210; --amber-t: #ffe2a8;
      --red: #6b1c1c; --red-t: #ffd0d0;
      --check: #343b48; --check-t: #d6dbe6;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 20px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  a { color: inherit; }
  .sub { color: var(--muted); font-size: 14px; margin-bottom: 14px; }
  .banner { background: var(--amber); color: var(--amber-t); border-radius: 10px;
            padding: 10px 14px; font-size: 14px; margin-bottom: 14px; }
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }
  .stat, .panel { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; }
  .stat .n { font-size: 26px; font-weight: 650; }
  .stat .l { color: var(--muted); font-size: 13px; }
  .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }
  .zone { border-radius: 12px; padding: 12px 14px; min-height: 96px; }
  .zone .id { font-size: 13px; opacity: 0.8; }
  .zone .count { font-size: 28px; font-weight: 650; }
  .zone .dens { font-size: 13px; }
  .zone .lvl { font-size: 12px; font-weight: 650; letter-spacing: 0.04em; }
  .GREEN, .CLEAR { background: var(--green); color: var(--green-t); }
  .AMBER, .BUSY { background: var(--amber); color: var(--amber-t); }
  .RED, .VERYBUSY { background: var(--red); color: var(--red-t); }
  .CHECK { background: var(--check); color: var(--check-t); }
  .cols { display: grid; grid-template-columns: 1.4fr 1fr; gap: 10px; margin-bottom: 10px; }
  .panel h2 { font-size: 15px; margin: 0 0 8px; }
  .alert { border-top: 1px solid var(--line); padding: 8px 0; font-size: 14px; }
  .alert:first-of-type { border-top: none; }
  .alert .t { color: var(--muted); font-size: 12px; }
  .alert .a { color: var(--muted); font-size: 13px; }
  .empty { color: var(--muted); font-size: 14px; }
  .site { display: flex; justify-content: space-between; align-items: center;
          border-top: 1px solid var(--line); padding: 7px 0; font-size: 14px; }
  .site:first-of-type { border-top: none; }
  .pill { border-radius: 999px; padding: 2px 10px; font-size: 12px; font-weight: 650; }
  .tag { color: var(--muted); font-size: 12px; margin-left: 6px; }
  svg { width: 100%; height: 100px; }
  @media (max-width: 760px) {
    .stats, .grid { grid-template-columns: repeat(2, 1fr); }
    .cols { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="wrap">
  <h1>Crowd Pilot AI: authority view</h1>
  <div class="sub">Prototype running on a looping test video. Not for real safety decisions.
    &nbsp;|&nbsp; <a href="/public" target="_blank">Open the public view</a></div>
  <div id="banner" class="banner" style="display:none">
    Floor areas are assumed, not measured. Densities and levels are illustrative until each camera is calibrated.
  </div>
  <div class="stats">
    <div class="stat"><div class="n" id="everyone">-</div><div class="l">everyone the model counts (3-reading average)</div></div>
    <div class="stat"><div class="n" id="inside">-</div><div class="l">inside the floor outline</div></div>
    <div class="stat"><div class="n" id="outside">-</div><div class="l">outside the outline (ignored)</div></div>
    <div class="stat"><div class="n" id="clock">-</div><div class="l">last update</div></div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="cols">
    <div class="panel">
      <h2>Alerts</h2>
      <div id="alerts"><div class="empty">No alerts yet.</div></div>
    </div>
    <div class="panel">
      <h2>People inside the floor outline, recent readings</h2>
      <svg id="chart" viewBox="0 0 300 120" preserveAspectRatio="none"></svg>
      <div class="sub" id="chartnote"></div>
    </div>
  </div>
  <div class="cols">
    <div class="panel">
      <h2>Pandals (A uses the camera, the rest are simulated)</h2>
      <div id="sites"></div>
    </div>
    <div class="panel">
      <h2>Recent public advice</h2>
      <div id="advisories"><div class="empty">Nobody has asked the public view yet.</div></div>
    </div>
  </div>
</div>
<script>
function setText(id, value) { document.getElementById(id).textContent = value; }
function cls(status) { return status.replace(" ", ""); }

function render(s) {
  if (!s.ready) { setText("clock", "starting..."); return; }
  document.getElementById("banner").style.display = s.calibrated ? "none" : "block";
  setText("everyone", s.everyone);
  setText("inside", s.inside);
  setText("outside", s.everyone - s.inside);
  setText("clock", s.clock);

  var grid = document.getElementById("grid");
  grid.innerHTML = "";
  s.zones.forEach(function (z) {
    var d = document.createElement("div");
    d.className = "zone " + z.level;
    d.innerHTML = "<div class='id'>Zone " + z.id + "</div>" +
      "<div class='count'>" + Math.round(z.count) + "</div>" +
      "<div class='dens'>" + z.density.toFixed(1) + " people/m2 (assumed area)</div>" +
      "<div class='lvl'>" + z.level + "</div>";
    grid.appendChild(d);
  });

  var box = document.getElementById("alerts");
  box.innerHTML = "";
  if (s.alerts.length === 0) {
    box.innerHTML = "<div class='empty'>No alerts yet.</div>";
  }
  s.alerts.slice(0, 8).forEach(function (a) {
    var d = document.createElement("div");
    d.className = "alert";
    var t = document.createElement("div"); t.className = "t"; t.textContent = a.clock + "  |  " + a.level;
    var m = document.createElement("div"); m.textContent = a.message;
    var x = document.createElement("div"); x.className = "a"; x.textContent = "Suggested: " + a.action;
    d.appendChild(t); d.appendChild(m); d.appendChild(x);
    box.appendChild(d);
  });

  var h = s.history;
  var chart = document.getElementById("chart");
  if (h.length > 1) {
    var max = Math.max.apply(null, h) * 1.1 || 1;
    var pts = h.map(function (v, i) {
      return (i / (h.length - 1) * 300).toFixed(1) + "," + (115 - (v / max) * 105).toFixed(1);
    }).join(" ");
    chart.innerHTML = "<polyline fill='none' stroke='#4c8bf5' stroke-width='2' points='" + pts + "'/>";
    setText("chartnote", "scale: 0 to " + Math.round(max) + " people");
  }

  var sb = document.getElementById("sites");
  sb.innerHTML = "";
  s.sites.forEach(function (x) {
    var d = document.createElement("div");
    d.className = "site";
    var left = document.createElement("div");
    left.textContent = x.name + "  " + x.people + " / " + x.capacity;
    var tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = x.live ? "camera" : "simulated";
    left.appendChild(tag);
    var pill = document.createElement("span");
    pill.className = "pill " + cls(x.status);
    pill.textContent = x.status + "  " + x.occupancy + "%";
    d.appendChild(left); d.appendChild(pill);
    sb.appendChild(d);
  });

  var ad = document.getElementById("advisories");
  ad.innerHTML = "";
  if (s.advisories.length === 0) {
    ad.innerHTML = "<div class='empty'>Nobody has asked the public view yet.</div>";
  }
  s.advisories.slice(0, 6).forEach(function (a) {
    var d = document.createElement("div");
    d.className = "alert";
    var t = document.createElement("div"); t.className = "t"; t.textContent = a.clock + "  |  " + a.gate;
    var m = document.createElement("div");
    m.textContent = a.redirected
      ? "Wanted " + a.want + ", sent to " + a.send
      : "Wanted " + a.want + ", advised: " + a.send;
    d.appendChild(t); d.appendChild(m);
    ad.appendChild(d);
  });
}

function tick() {
  fetch("/api/state").then(function (r) { return r.json(); }).then(render).catch(function () {});
}
tick();
setInterval(tick, 1000);
</script>
</body>
</html>
"""

PUBLIC_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pandal crowd guide (demo)</title>
<style>
  :root {
    --bg: #f5f6f8; --card: #ffffff; --text: #1b1f24; --muted: #667085; --line: #dfe3e8;
    --green: #d7f0dc; --green-t: #14532d;
    --amber: #fde8c0; --amber-t: #7a4a00;
    --red: #f9d0d0; --red-t: #8a1111;
    --btn: #2563eb;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #12151a; --card: #1b2028; --text: #eceff4; --muted: #98a2b3; --line: #2c3340;
      --green: #1d4a2b; --green-t: #c7f0d2;
      --amber: #5a4210; --amber-t: #ffe2a8;
      --red: #6b1c1c; --red-t: #ffd0d0;
      --btn: #3b82f6;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  .wrap { max-width: 520px; margin: 0 auto; padding: 18px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .sub { color: var(--muted); font-size: 14px; margin-bottom: 14px; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 14px;
          padding: 14px; margin-bottom: 12px; }
  .card h2 { font-size: 16px; margin: 0 0 10px; }
  .row { display: flex; justify-content: space-between; align-items: center;
         border-top: 1px solid var(--line); padding: 9px 0; }
  .row:first-of-type { border-top: none; }
  .pill { border-radius: 999px; padding: 3px 12px; font-size: 13px; font-weight: 650; }
  .CLEAR { background: var(--green); color: var(--green-t); }
  .BUSY { background: var(--amber); color: var(--amber-t); }
  .VERYBUSY { background: var(--red); color: var(--red-t); }
  label { display: block; font-size: 13px; color: var(--muted); margin: 8px 0 4px; }
  select, button { width: 100%; font-size: 16px; padding: 10px; border-radius: 10px;
                   border: 1px solid var(--line); background: var(--card); color: var(--text); }
  button { background: var(--btn); color: #fff; border: none; margin-top: 12px; font-weight: 650; }
  #answer { margin-top: 12px; font-size: 16px; line-height: 1.4; }
  .note { color: var(--muted); font-size: 12px; margin-top: 10px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Pandal crowd guide</h1>
  <div class="sub">Demo. Pandal A uses a test camera feed. The others are simulated.</div>

  <div class="card">
    <h2>Right now</h2>
    <div id="sites"></div>
  </div>

  <div class="card">
    <h2>Plan your visit</h2>
    <label for="gate">Where are you entering?</label>
    <select id="gate"></select>
    <label for="want">Which pandal do you want to see?</label>
    <select id="want"></select>
    <button id="go">Check the best way</button>
    <div id="answer"></div>
  </div>

  <div class="note">Demo data, not real advice. Statuses refresh every few seconds.</div>
</div>
<script>
function cls(status) { return status.replace(" ", ""); }
var filled = false;

function load() {
  fetch("/api/sites").then(function (r) { return r.json(); }).then(function (d) {
    var box = document.getElementById("sites");
    box.innerHTML = "";
    d.sites.forEach(function (s) {
      var row = document.createElement("div"); row.className = "row";
      var name = document.createElement("div"); name.textContent = s.name;
      var pill = document.createElement("span");
      pill.className = "pill " + cls(s.status);
      pill.textContent = s.status;
      row.appendChild(name); row.appendChild(pill);
      box.appendChild(row);
    });
    if (!filled) {
      var g = document.getElementById("gate");
      d.gates.forEach(function (x) {
        var o = document.createElement("option"); o.value = x; o.textContent = x; g.appendChild(o);
      });
      var w = document.getElementById("want");
      d.sites.forEach(function (s) {
        var o = document.createElement("option"); o.value = s.id; o.textContent = s.name; w.appendChild(o);
      });
      filled = true;
    }
  }).catch(function () {});
}

document.getElementById("go").addEventListener("click", function () {
  var gate = document.getElementById("gate").value;
  var want = document.getElementById("want").value;
  fetch("/api/recommend?gate=" + encodeURIComponent(gate) + "&want=" + encodeURIComponent(want))
    .then(function (r) { return r.json(); })
    .then(function (a) { document.getElementById("answer").textContent = a.message; })
    .catch(function () { document.getElementById("answer").textContent = "Could not check right now."; });
});

load();
setInterval(load, 3000);
</script>
</body>
</html>
"""


DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
INDEX_FILE = os.path.join(DIST_DIR, "index.html")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")

if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/favicon.svg")
def favicon():
    fav = os.path.join(DIST_DIR, "favicon.svg")
    if os.path.isfile(fav):
        return FileResponse(fav)
    raise HTTPException(status_code=404)


@app.get("/")
def dashboard():
    if os.path.isfile(INDEX_FILE):
        return FileResponse(INDEX_FILE)
    return HTMLResponse(DASHBOARD_HTML)


@app.get("/public")
def public_page():
    if os.path.isfile(INDEX_FILE):
        return FileResponse(INDEX_FILE)
    return HTMLResponse(PUBLIC_HTML)


if __name__ == "__main__":
    with lock:
        publish_sites()
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=sim_worker, daemon=True).start()
    print("Authority view: http://127.0.0.1:8000")
    print("Public view:    http://127.0.0.1:8000/public")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")