import { useState, useCallback, useEffect } from "react";
import {
  Compass,
  ArrowRight,
  AlertCircle,
  Clock,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  Layers,
} from "lucide-react";
import type { PublicSitesResponse, RecommendationResponse } from "../types";
import { fetchPublicSites, fetchRecommendation } from "../api";
import { usePolling } from "../usePolling";

interface PublicViewProps {
  onNavigate: (path: string) => void;
}

export function PublicView({ onNavigate }: PublicViewProps) {
  const fetcher = useCallback((signal: AbortSignal) => fetchPublicSites(signal), []);
  const { data, error, isLoading, isStale, refresh } = usePolling<PublicSitesResponse>(fetcher, 3000);

  const [selectedGate, setSelectedGate] = useState<string>("");
  const [selectedSite, setSelectedSite] = useState<string>("");
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Set default form select values once data loads
  useEffect(() => {
    if (data && data.gates.length > 0 && !selectedGate) {
      setSelectedGate(data.gates[0]);
    }
    if (data && data.sites.length > 0 && !selectedSite) {
      setSelectedSite(data.sites[0].id);
    }
  }, [data, selectedGate, selectedSite]);

  const handlePlanVisit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGate || !selectedSite) return;

    setIsSubmitting(true);
    setFormError(null);
    try {
      const result = await fetchRecommendation(selectedGate, selectedSite);
      setRecommendation(result);
      // Refresh status list to reflect new pending crowd movements
      refresh();
    } catch {
      setFormError("Could not retrieve route recommendation right now. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const s = status.toUpperCase();
    if (s === "CLEAR") {
      return (
        <span className="px-3.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-600/40">
          CLEAR
        </span>
      );
    }
    if (s === "BUSY") {
      return (
        <span className="px-3.5 py-1 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-600/40">
          BUSY
        </span>
      );
    }
    if (s === "VERY BUSY") {
      return (
        <span className="px-3.5 py-1 rounded-full text-xs font-semibold bg-rose-950/80 text-rose-300 border border-rose-600/40">
          VERY BUSY
        </span>
      );
    }
    if (s === "CLOSED") {
      return (
        <span className="px-3.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-600">
          CLOSED
        </span>
      );
    }
    return (
      <span className="px-3.5 py-1 rounded-full text-xs font-semibold bg-gray-800 text-gray-300">
        {status}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans flex flex-col items-center justify-between p-4 sm:p-6 selection:bg-blue-500 selection:text-white">
      <div className="w-full max-w-[440px] my-auto space-y-5">
        {/* Top Navigation / Brand */}
        <header className="flex items-center justify-between pt-2 pb-1">
          <div>
            <div className="flex items-center gap-2">
              <Compass className="text-blue-400" size={24} />
              <h1 className="text-xl font-bold tracking-tight text-white">Pandal Crowd Guide</h1>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              Demo capacity status and calm route recommendations.
            </p>
          </div>

          <button
            onClick={() => onNavigate("/")}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-gray-900 border border-gray-800 text-gray-300 hover:text-white hover:bg-gray-800 transition-colors cursor-pointer"
            title="Switch to Authority Control Dashboard"
          >
            <Layers size={14} />
            <span className="hidden sm:inline">Authority</span>
          </button>
        </header>

        {/* Global Service Error Banner */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-950/80 border border-rose-600/80 text-rose-200 text-xs flex items-start gap-3">
            <AlertCircle size={18} className="text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-100">Cannot reach the vision service. Is python server.py running?</p>
              <p className="text-rose-300 mt-1">
                Please verify that the backend server is active.
              </p>
            </div>
          </div>
        )}

        {/* Stale Data Indicator */}
        {!error && isStale && (
          <div className="p-3 rounded-xl bg-amber-950/70 border border-amber-600/60 text-amber-200 text-xs flex items-center gap-2.5">
            <Clock size={16} className="text-amber-400 shrink-0" />
            <span>Connection paused. Data may be older than 10 seconds.</span>
          </div>
        )}

        {/* Initial Loading State */}
        {!error && isLoading && !data && (
          <div className="p-6 rounded-2xl bg-gray-900/80 border border-gray-800 text-center">
            <RefreshCw className="animate-spin text-blue-400 mx-auto mb-2" size={24} />
            <p className="text-xs text-gray-300 font-medium">Model is loading, about 20 seconds...</p>
            <p className="text-[11px] text-gray-500 mt-0.5">Fetching latest pandal availability</p>
          </div>
        )}

        {/* Pandals Live Status Card */}
        {data && (
          <section className="p-5 rounded-2xl bg-gray-900/80 border border-gray-800 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
                Current Status
              </h2>
              <span className="text-[11px] text-gray-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Demo data, refreshes every few seconds
              </span>
            </div>

            <div className="divide-y divide-gray-800/80">
              {data.sites.map((site) => (
                <div
                  key={site.id}
                  className="py-3.5 flex items-center justify-between min-h-[50px]"
                >
                  <span className="font-medium text-white text-base">{site.name}</span>
                  <div>{getStatusBadge(site.status)}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Plan Your Visit Interactive Form */}
        {data && (
          <section className="p-5 rounded-2xl bg-gray-900/80 border border-gray-800 shadow-sm">
            <h2 className="text-base font-bold text-white mb-1 flex items-center gap-2">
              <ShieldCheck size={18} className="text-blue-400" />
              Plan Your Visit
            </h2>
            <p className="text-xs text-gray-400 mb-4">
              Select your entry point to discover the smoothest route.
            </p>

            <form onSubmit={handlePlanVisit} className="space-y-4">
              <div>
                <label htmlFor="gate-select" className="block text-xs font-semibold text-gray-300 mb-1.5">
                  Where are you entering?
                </label>
                <select
                  id="gate-select"
                  value={selectedGate}
                  onChange={(e) => setSelectedGate(e.target.value)}
                  className="w-full h-12 px-3.5 rounded-xl bg-gray-950 border border-gray-700 text-white text-sm focus:outline-none focus:border-blue-500 transition-colors cursor-pointer"
                >
                  {data.gates.map((g) => (
                    <option key={g} value={g}>
                      {g}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="want-select" className="block text-xs font-semibold text-gray-300 mb-1.5">
                  Which pandal do you want to see?
                </label>
                <select
                  id="want-select"
                  value={selectedSite}
                  onChange={(e) => setSelectedSite(e.target.value)}
                  className="w-full h-12 px-3.5 rounded-xl bg-gray-950 border border-gray-700 text-white text-sm focus:outline-none focus:border-blue-500 transition-colors cursor-pointer"
                >
                  {data.sites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.status})
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !selectedGate || !selectedSite}
                className="w-full h-12 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm transition-all duration-150 flex items-center justify-center gap-2 shadow-lg shadow-blue-900/30 cursor-pointer disabled:opacity-50"
              >
                {isSubmitting ? (
                  <RefreshCw size={18} className="animate-spin" />
                ) : (
                  <>
                    <span>Check the best way</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>

            {/* Form Error */}
            {formError && (
              <div className="mt-4 p-3 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 text-xs">
                {formError}
              </div>
            )}

            {/* Recommendation Result */}
            {recommendation && (
              <div className="mt-4 p-4 rounded-xl bg-blue-950/50 border border-blue-500/40 text-blue-100 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-blue-300 flex items-center gap-1.5">
                    <CheckCircle2 size={14} className="text-blue-400" />
                    Recommended Route
                  </span>
                  {recommendation.redirected && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-semibold border border-amber-500/40">
                      Rerouted
                    </span>
                  )}
                </div>

                <p className="text-sm font-medium leading-relaxed text-white">
                  {recommendation.message}
                </p>

                {recommendation.minutes !== null && (
                  <div className="text-xs text-blue-300 pt-1 border-t border-blue-900/40 flex items-center justify-between">
                    <span>Estimated walking time</span>
                    <span className="font-bold text-white">~{recommendation.minutes} minutes</span>
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {/* Prototype Transparency Footnote */}
        <footer className="text-center text-[11px] text-gray-400 leading-normal px-2 pt-2">
          Demo data, not real safety advice. Pandal A uses a test video feed; others are simulated.
        </footer>
      </div>
    </div>
  );
}
