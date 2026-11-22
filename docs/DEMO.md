# Crowd Pilot AI — 2-Minute Screen Recording Demo Script

A step-by-step guide for recording a concise, two-minute walkthrough of the Crowd Pilot AI prototype.

---

## Preparation
1. Start the single-server production instance:
   ```bash
   cd frontend && npm run build
   cd ../cv-service && source .venv/bin/activate
   python server.py
   ```
2. Open two browser tabs or side-by-side windows:
   - **Authority Dashboard**: `http://127.0.0.1:8000/`
   - **Public Guide**: `http://127.0.0.1:8000/public`
3. Wait ~20 seconds for the CSRNet model weights to load and the status to show live data.

---

## Script & Timeline (0:00 – 2:00)

### 0:00 – 0:30 | The Authority Dashboard & Zone Grid
**Screen:** Authority View at `http://127.0.0.1:8000/`  
**Action:** Mouse over the top stat cards and the 3×4 zone grid.

> **Voiceover:**
> *"Welcome to Crowd Pilot AI, an early prototype designed to assist festival organizers and police during large public gatherings like Durga Puja pandals in Kolkata.*
>
> *On the main Authority dashboard, notice the four top stat cards. Crucially, we distinguish between 'everyone counted' by the CSRNet model and 'inside floor outline'. In dense venue video, nearly half of detected individuals may be outside glass windows or beyond security gates. We only calculate crowd metrics on the walkable floor.*
>
> *Below is the 3×4 zone density grid. Unlike naive headcount systems, crush risk depends strictly on density—people per square meter. Each zone displays current density and status levels: Green for normal, Amber for elevated, Red for congested, and Check for sensor anomalies."*

---

### 0:30 – 0:55 | The Calibration Banner & Alert Logic
**Screen:** Zoom or highlight the amber warning banner at the top and the Alerts panel.  
**Action:** Scroll slightly down to show the Alerts & Suggested Actions list and History chart.

> **Voiceover:**
> *"Notice this prominent yellow banner: 'Floor areas are assumed, not measured.' To calculate true density, each camera perspective requires ground-plane homography calibration. Until measured reference points are set, all zone levels are illustrative.*
>
> *In the Alerts panel, notice that alerts do not trigger instantly on momentary spikes. Our threshold engine uses hysteresis—a zone must remain RED for 3 consecutive readings before raising an alarm. Each alert pairs with a concrete operational action, such as limiting entry at a nearby gate or activating a diversion."*

---

### 0:55 – 1:25 | Authority Control: Closing a Pandal
**Screen:** Pandals Status & Capacity Control panel.  
**Action:** Click the red **"Close"** button next to Pandal B. When the browser prompt asks for the admin PIN, type `1234` and hit Enter.

> **Voiceover:**
> *"Let's simulate an operational scenario. Organizers need to temporarily close Pandal B due to queue spillover.*
>
> *I click 'Close'. The system prompts for an administrative PIN. Entering our demo PIN 1234 immediately updates Pandal B's status to CLOSED across the network. Notice that an ADMIN alert is instantly logged in the alert stream, informing all duty officers that the public guide will now automatically redirect visitors away from Pandal B."*

---

### 1:25 – 1:45 | Public Guide & Capacity-Aware Rerouting
**Screen:** Switch to Public Guide tab at `http://127.0.0.1:8000/public` (viewed at mobile width ~390px).  
**Action:** Show the status list. Under "Plan your visit", select **North gate** and **Pandal B**, then click **"Check the best way"**.

> **Voiceover:**
> *"Now let's switch to the Public Guide, designed mobile-first for visitors on their phones.*
>
> *First, notice that the public never sees raw headcount numbers—only clear, calm words like CLEAR, BUSY, or CLOSED. Pandal B reflects the closure we just enacted.*
>
> *If a visitor enters at North Gate and requests Pandal B, our routing engine does not simply send them to a closed venue. It recalculates walking times and capacity across all open pavilions, advising them to proceed to Pandal D instead to prevent entrance crowding."*

---

### 1:45 – 2:00 | Honest Limitations & Next Steps
**Screen:** Switch back to the Authority Dashboard overview.

> **Voiceover:**
> *"To be completely transparent about our status: this is an early prototype. Pandal A runs on a looping test clip, while Pandals B through E are simulated. Converting this to a deployed safety system requires formal camera calibration, multi-camera tracking, and partnerships with local authorities.*
>
> *Crowd Pilot AI demonstrates how computer vision and capacity-aware routing can collaborate to keep crowds safe and moving smoothly."*
