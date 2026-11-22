import { useState, useCallback } from "react";
import {
  AlertTriangle,
  Users,
  Clock,
  ShieldAlert,
  ArrowRight,
  RefreshCw,
  Lock,
  Unlock,
  AlertCircle,
  Activity,
  Layers,
} from "lucide-react";
import type { AppState, Site, Zone } from "../types";
import { fetchState, setSiteClosed, ApiError } from "../api";
import { usePolling } from "../usePolling";

interface AuthorityViewProps {
  onNavigate: (path: string) => void;
}

export function AuthorityView({ onNavigate }: AuthorityViewProps) {
  const fetcher = useCallback((signal: AbortSignal) => fetchState(signal), []);
  const { data, error, isLoading, isStale, refresh } = usePolling<AppState>(fetcher, 1000);

  // Demo admin PIN kept strictly in component memory
  const [adminPin, setAdminPin] = useState<string | null>(null);
  const [pinError, setPinError] = useState<string | null>(null);
  const [updatingSite, setUpdatingSite] = useState<string | null>(null);

  // Compute overall risk from zone statuses
  const computeOverallRisk = (zones: Zone[]): { label: string; color: string; bg: string; border: string } => {
    if (!zones || zones.length === 0) {
      return { label: "INITIALIZING", color: "text-gray-400", bg: "bg-gray-800/40", border: "border-gray-700" };
    }
    if (zones.some((z) => z.level === "RED")) {
      return { label: "RISK LEVEL: HIGH", color: "text-red-400", bg: "bg-red-950/60", border: "border-red-600" };
    }
    if (zones.some((z) => z.level === "AMBER")) {
      return { label: "RISK LEVEL: ELEVATED", color: "text-amber-400", bg: "bg-amber-950/60", border: "border-amber-600" };
    }
    if (zones.some((z) => z.level === "CHECK")) {
      return { label: "ATTENTION: SENSOR CHECK", color: "text-slate-300", bg: "bg-slate-800/60", border: "border-slate-600" };
    }
    return { label: "RISK LEVEL: NORMAL", color: "text-emerald-400", bg: "bg-emerald-950/60", border: "border-emerald-600" };
  };

  const handleToggleClosed = async (site: Site) => {
    setPinError(null);
    let pin = adminPin;

    if (!pin) {
      const input = window.prompt("Enter admin PIN to modify pandal status (demo: 1234):");
      if (!input) return;
      pin = input.trim();
    }

    setUpdatingSite(site.id);
    try {
      await setSiteClosed({
        site: site.id,
        closed: !site.closed,
        pin,
      });
      // Store PIN in memory upon success
      setAdminPin(pin);
      refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setAdminPin(null); // Clear memory on 403
        setPinError("Wrong PIN entered. Action denied.");
      } else {
        setPinError(err instanceof Error ? err.message : "Failed to update pandal status.");
      }
    } finally {
      setUpdatingSite(null);
    }
  };

  const overallRisk = data ? computeOverallRisk(data.zones) : null;

  return (
    <div className="flex flex-col md:flex-row min-h-screen bg-gray-950 text-gray-100 font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-full md:w-64 border-b md:border-b-0 md:border-r border-gray-800 bg-gray-900/70 p-6 flex flex-col justify-between shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <ShieldAlert className="text-red-500" size={26} />
            <span className="text-xl font-bold tracking-tight text-white">Crowd Pilot AI</span>
          </div>
          <p className="text-xs text-gray-400 mb-8 leading-relaxed">
            Real-time crowd safety & zone density monitoring for festival pandals.
          </p>

          <nav className="space-y-2">
            <button
              onClick={() => onNavigate("/")}
              className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium bg-red-600/20 text-red-400 border border-red-500/30 cursor-pointer"
            >
              <div className="flex items-center gap-3">
                <Layers size={18} />
                <span>Authority View</span>
              </div>
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
            </button>

            <button
              onClick={() => onNavigate("/public")}
              className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:text-gray-200 hover:bg-gray-800/60 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-3">
                <Users size={18} />
                <span>Public Guide</span>
              </div>
              <ArrowRight size={15} className="text-gray-500" />
            </button>
          </nav>
        </div>

        <div className="mt-8 pt-4 border-t border-gray-800/80 text-xs text-gray-400">
          <div className="flex items-center justify-between mb-1">
            <span>Status</span>
            <span className={`inline-flex items-center gap-1.5 font-medium ${error ? "text-rose-400" : isStale ? "text-amber-400" : "text-emerald-400"}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${error ? "bg-rose-400" : isStale ? "bg-amber-400 animate-ping" : "bg-emerald-400"}`}></span>
              {error ? "Offline" : isStale ? "Stale Data" : "Live (1s)"}
            </span>
          </div>
          <p className="text-[11px] text-gray-400">Pandal A: live camera feed<br />Pandals B–E: simulated</p>
        </div>
      </aside>

      {/* Main Content Dashboard */}
      <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
        {/* Header Bar */}
        <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              Authority Live Control
            </h1>
            <p className="text-sm text-gray-400">
              Prototype running on a looping test video. Not for actual emergency life-safety decisions.
            </p>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {overallRisk && (
              <div
                className={`px-3 py-1.5 rounded-lg border text-xs font-semibold tracking-wide flex items-center gap-2 ${overallRisk.bg} ${overallRisk.border} ${overallRisk.color}`}
              >
                <AlertTriangle size={15} />
                <span>{overallRisk.label}</span>
              </div>
            )}
            <button
              onClick={() => refresh()}
              title="Force refresh"
              className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors cursor-pointer"
            >
              <RefreshCw size={16} className={isLoading ? "animate-spin" : ""} />
            </button>
          </div>
        </header>

        {/* Global Error Banner */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-950/80 border border-rose-600/80 text-rose-200 flex items-start gap-3">
            <AlertCircle size={20} className="text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-100">Cannot reach the vision service. Is python server.py running?</p>
              <p className="text-xs text-rose-300 mt-1">
                Make sure cv-service is running (<code className="bg-rose-900/60 px-1 py-0.5 rounded">cd cv-service && source .venv/bin/activate && python server.py</code>).
              </p>
            </div>
          </div>
        )}

        {/* Stale Data Warning Banner */}
        {!error && isStale && (
          <div className="mb-6 p-3.5 rounded-xl bg-amber-950/70 border border-amber-600/60 text-amber-200 flex items-center gap-3 text-sm">
            <Clock size={18} className="text-amber-400 shrink-0" />
            <span>
              <strong>Warning:</strong> No successful update received for over 10 seconds. Data shown below may be stale.
            </span>
          </div>
        )}

        {/* Loading / Vision Initialization State */}
        {!error && (!data || !data.ready) && (
          <div className="mb-6 p-6 rounded-xl bg-gray-900/90 border border-gray-800 text-center flex flex-col items-center justify-center">
            <Activity className="text-amber-400 animate-spin mb-3" size={32} />
            <h3 className="text-base font-semibold text-gray-200">Vision model is loading...</h3>
            <p className="text-sm text-gray-400 mt-1 max-w-md">
              Loading CSRNet weights and starting video inference pipeline (about 20 seconds). Live statistics will appear automatically.
            </p>
          </div>
        )}

        {/* Uncalibrated Camera Warning Banner */}
        {data && !data.calibrated && (
          <div className="mb-6 p-3.5 rounded-xl bg-amber-950/50 border border-amber-500/40 text-amber-300 flex items-start gap-3 text-sm">
            <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-medium">Uncalibrated Camera Feed:</span> Floor areas are assumed, not measured. Densities and risk levels are illustrative until ground-plane homography calibration is performed.
            </div>
          </div>
        )}

        {/* PIN Action Feedback Banner */}
        {pinError && (
          <div className="mb-6 p-3 rounded-lg bg-red-950/70 border border-red-500/50 text-red-200 text-xs flex items-center justify-between">
            <span>{pinError}</span>
            <button onClick={() => setPinError(null)} className="text-red-400 hover:text-red-200 font-bold ml-2">Dismiss</button>
          </div>
        )}

        {data && (
          <div className="space-y-6">
            {/* Stat Cards (4 Cards) */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 shadow-sm">
                <div className="text-xs text-gray-400 font-medium">Everyone Counted</div>
                <div className="text-2xl sm:text-3xl font-bold text-white mt-1">{data.everyone}</div>
                <div className="text-[11px] text-gray-400 mt-1">3-reading model average</div>
              </div>

              <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 shadow-sm">
                <div className="text-xs text-gray-400 font-medium">Inside Floor Outline</div>
                <div className="text-2xl sm:text-3xl font-bold text-emerald-400 mt-1">{data.inside}</div>
                <div className="text-[11px] text-gray-400 mt-1">Walkable pavilion area</div>
              </div>

              <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 shadow-sm">
                <div className="text-xs text-gray-400 font-medium">Outside Floor Outline</div>
                <div className="text-2xl sm:text-3xl font-bold text-gray-300 mt-1">{data.everyone - data.inside}</div>
                <div className="text-[11px] text-gray-400 mt-1">Ignored (doors, streets)</div>
              </div>

              <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 shadow-sm">
                <div className="text-xs text-gray-400 font-medium">Last Update</div>
                <div className="text-2xl sm:text-3xl font-bold text-white mt-1 font-mono">{data.clock || "--:--:--"}</div>
                <div className="text-[11px] text-gray-400 mt-1">Video time: {data.video_time}s</div>
              </div>
            </div>

            {/* 3x4 Zone Density Grid */}
            <section className="p-5 rounded-xl bg-gray-900/80 border border-gray-800">
              <div className="flex flex-col sm:flex-row justify-between sm:items-center mb-4 gap-2">
                <div>
                  <h2 className="text-base font-semibold text-white">Zone Density Map (3 Rows × 4 Cols)</h2>
                  <p className="text-xs text-gray-400">
                    Floor subdivided into 12 zones. Levels trigger based on density thresholds (Green &lt; 2, Amber 2–4, Red ≥ 4).
                  </p>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-400">
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> GREEN</span>
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> AMBER</span>
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span> RED</span>
                  <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-slate-500"></span> CHECK</span>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {data.zones.map((zone) => {
                  let style = {
                    bg: "bg-emerald-950/40",
                    border: "border-emerald-600/40",
                    text: "text-emerald-300",
                    badge: "bg-emerald-900/60 text-emerald-300",
                  };
                  if (zone.level === "AMBER") {
                    style = {
                      bg: "bg-amber-950/40",
                      border: "border-amber-600/40",
                      text: "text-amber-300",
                      badge: "bg-amber-900/60 text-amber-300",
                    };
                  } else if (zone.level === "RED") {
                    style = {
                      bg: "bg-rose-950/50",
                      border: "border-rose-600/60",
                      text: "text-rose-300",
                      badge: "bg-rose-900/80 text-rose-200",
                    };
                  } else if (zone.level === "CHECK") {
                    style = {
                      bg: "bg-slate-900/60",
                      border: "border-slate-600/50",
                      text: "text-slate-300",
                      badge: "bg-slate-800 text-slate-300",
                    };
                  }

                  return (
                    <div
                      key={zone.id}
                      className={`p-3.5 rounded-xl border flex flex-col justify-between min-h-[105px] transition-all ${style.bg} ${style.border}`}
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-gray-400">Zone {zone.id}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full tracking-wider ${style.badge}`}>
                          {zone.level}
                        </span>
                      </div>

                      <div className="my-1">
                        <div className="text-2xl font-bold tracking-tight text-white">
                          {Math.round(zone.count)}
                          <span className="text-xs font-normal text-gray-400 ml-1">people</span>
                        </div>
                      </div>

                      <div className="text-xs text-gray-400">
                        <span className={`font-semibold ${style.text}`}>{zone.density.toFixed(1)}</span> people/m²
                        {!data.calibrated && <span className="block text-[10px] text-gray-400 opacity-80">(assumed area)</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Split Grid: Alerts & Inside Floor History */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Alerts Panel */}
              <section className="p-5 rounded-xl bg-gray-900/80 border border-gray-800 flex flex-col">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-base font-semibold text-white flex items-center gap-2">
                    <AlertTriangle size={18} className="text-red-400" />
                    Alerts & Suggested Actions
                  </h2>
                  <span className="text-xs text-gray-400">{data.alerts.length} logged</span>
                </div>

                <div className="space-y-2.5 overflow-y-auto max-h-[280px] pr-1">
                  {data.alerts.length === 0 ? (
                    <div className="p-6 text-center text-sm text-gray-400 border border-dashed border-gray-800 rounded-lg">
                      No active alerts. All monitored zones are within safe density limits.
                    </div>
                  ) : (
                    data.alerts.slice(0, 10).map((a, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-gray-950/60 border border-gray-800 text-xs flex flex-col gap-1.5"
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-mono text-gray-400">{a.clock}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${
                              a.level === "RED"
                                ? "bg-rose-950 text-rose-300 border border-rose-800"
                                : a.level === "CHECK"
                                ? "bg-slate-800 text-slate-300"
                                : "bg-gray-800 text-gray-300"
                            }`}
                          >
                            {a.level}
                          </span>
                        </div>
                        <div className="text-gray-200 font-medium">{a.message}</div>
                        {a.action && (
                          <div className="text-amber-300/90 font-medium bg-amber-950/30 px-2 py-1 rounded border border-amber-900/40">
                            Suggested action: {a.action}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </section>

              {/* Inside Floor History Chart */}
              <section className="p-5 rounded-xl bg-gray-900/80 border border-gray-800 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="text-base font-semibold text-white">Inside Floor History</h2>
                    <span className="text-xs text-gray-400">Past {data.history.length} readings</span>
                  </div>
                  <p className="text-xs text-gray-400 mb-4">
                    Trend of people inside the defined floor outline over time.
                  </p>
                </div>

                {/* Inline SVG Chart */}
                <div className="relative w-full h-[140px] bg-gray-950/80 rounded-lg p-2 border border-gray-800/80 flex flex-col justify-end">
                  {data.history.length > 1 ? (
                    (() => {
                      const max = Math.max(...data.history) * 1.15 || 10;
                      const h = data.history;
                      const width = 300;
                      const height = 110;
                      const points = h
                        .map((v, i) => {
                          const x = ((i / (h.length - 1)) * width).toFixed(1);
                          const y = (height - (v / max) * (height - 15) - 5).toFixed(1);
                          return `${x},${y}`;
                        })
                        .join(" ");

                      return (
                        <div className="w-full h-full flex flex-col justify-between">
                          <svg
                            viewBox={`0 0 ${width} ${height}`}
                            preserveAspectRatio="none"
                            className="w-full h-full overflow-visible"
                          >
                            {/* Horizontal guide lines */}
                            <line x1="0" y1="20" x2={width} y2="20" stroke="#374151" strokeDasharray="3,3" strokeWidth="1" />
                            <line x1="0" y1="60" x2={width} y2="60" stroke="#374151" strokeDasharray="3,3" strokeWidth="1" />
                            <line x1="0" y1="100" x2={width} y2="100" stroke="#374151" strokeDasharray="3,3" strokeWidth="1" />

                            {/* History line */}
                            <polyline
                              fill="none"
                              stroke="#3b82f6"
                              strokeWidth="2.5"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              points={points}
                            />
                          </svg>
                          <div className="flex justify-between items-center text-[10px] text-gray-400 mt-1 font-mono">
                            <span>0</span>
                            <span>scale: 0 to {Math.round(max)} people</span>
                          </div>
                        </div>
                      );
                    })()
                  ) : (
                    <div className="h-full flex items-center justify-center text-xs text-gray-400">
                      Collecting history points...
                    </div>
                  )}
                </div>
              </section>
            </div>

            {/* Split Grid: Pandals Control Panel & Recent Public Advice */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Pandals Panel with Close/Reopen Controls */}
              <section className="p-5 rounded-xl bg-gray-900/80 border border-gray-800">
                <div className="flex justify-between items-center mb-3">
                  <div>
                    <h2 className="text-base font-semibold text-white">Pandals Status & Capacity Control</h2>
                    <p className="text-xs text-gray-400">Pandal A uses the camera; B–E are simulated.</p>
                  </div>
                </div>

                <div className="divide-y divide-gray-800/80">
                  {data.sites.map((site) => {
                    const isClosed = site.status === "CLOSED" || site.closed;
                    let pillStyle = "bg-emerald-950/80 text-emerald-300 border-emerald-600/40";
                    if (isClosed) {
                      pillStyle = "bg-slate-800 text-slate-300 border-slate-600";
                    } else if (site.status === "VERY BUSY") {
                      pillStyle = "bg-rose-950/80 text-rose-300 border-rose-600/40";
                    } else if (site.status === "BUSY") {
                      pillStyle = "bg-amber-950/80 text-amber-300 border-amber-600/40";
                    }

                    return (
                      <div key={site.id} className="py-3 flex items-center justify-between gap-3 text-sm">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-white">{site.name}</span>
                          <span className="text-xs text-gray-400">
                            {site.people} / {site.capacity}
                          </span>
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                              site.live ? "bg-blue-950 text-blue-300 border border-blue-800" : "bg-gray-800 text-gray-400"
                            }`}
                          >
                            {site.live ? "camera" : "simulated"}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${pillStyle}`}>
                            {site.status} {!isClosed ? `${site.occupancy}%` : ""}
                          </span>

                          <button
                            onClick={() => handleToggleClosed(site)}
                            disabled={updatingSite === site.id}
                            className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50 ${
                              isClosed
                                ? "bg-emerald-700 hover:bg-emerald-600 text-white"
                                : "bg-rose-700 hover:bg-rose-600 text-white"
                            }`}
                          >
                            {isClosed ? (
                              <>
                                <Unlock size={13} />
                                <span>Reopen</span>
                              </>
                            ) : (
                              <>
                                <Lock size={13} />
                                <span>Close</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* Recent Public Advice Panel */}
              <section className="p-5 rounded-xl bg-gray-900/80 border border-gray-800">
                <div className="flex justify-between items-center mb-3">
                  <div>
                    <h2 className="text-base font-semibold text-white">Recent Public Advice</h2>
                    <p className="text-xs text-gray-400">Recommendations dispatched by the public guide.</p>
                  </div>
                  <span className="text-xs text-gray-400">{data.advisories.length} logged</span>
                </div>

                <div className="space-y-2.5 overflow-y-auto max-h-[280px] pr-1">
                  {data.advisories.length === 0 ? (
                    <div className="p-6 text-center text-sm text-gray-400 border border-dashed border-gray-800 rounded-lg">
                      Nobody has asked the public view yet.
                    </div>
                  ) : (
                    data.advisories.slice(0, 8).map((adv, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-gray-950/60 border border-gray-800 text-xs flex flex-col gap-1"
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-mono text-gray-400">{adv.clock}</span>
                          <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 font-medium text-[11px]">
                            {adv.gate}
                          </span>
                        </div>
                        <div className="text-gray-200 mt-0.5">
                          {adv.redirected ? (
                            <span>
                              Wanted <strong className="text-white">{adv.want}</strong>, redirected to{" "}
                              <strong className="text-emerald-300">{adv.send}</strong>
                            </span>
                          ) : (
                            <span>
                              Wanted <strong className="text-white">{adv.want}</strong>, advised:{" "}
                              <strong className="text-white">{adv.send}</strong>
                            </span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </section>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
