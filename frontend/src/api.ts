import type {
  AppState,
  PublicSitesResponse,
  RecommendationResponse,
  AdminClosedRequest,
  AdminClosedResponse,
} from "./types";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export async function fetchState(signal?: AbortSignal): Promise<AppState> {
  const res = await fetch("/api/state", { signal });
  if (!res.ok) {
    throw new ApiError(`Failed to fetch state: ${res.statusText}`, res.status);
  }
  return res.json();
}

export async function fetchPublicSites(signal?: AbortSignal): Promise<PublicSitesResponse> {
  const res = await fetch("/api/sites", { signal });
  if (!res.ok) {
    throw new ApiError(`Failed to fetch sites: ${res.statusText}`, res.status);
  }
  return res.json();
}

export async function fetchRecommendation(
  gate: string,
  want: string,
  signal?: AbortSignal
): Promise<RecommendationResponse> {
  const params = new URLSearchParams({ gate, want });
  const res = await fetch(`/api/recommend?${params.toString()}`, { signal });
  if (!res.ok) {
    throw new ApiError(`Failed to get recommendation: ${res.statusText}`, res.status);
  }
  return res.json();
}

export async function setSiteClosed(
  req: AdminClosedRequest,
  signal?: AbortSignal
): Promise<AdminClosedResponse> {
  const res = await fetch("/api/admin/closed", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok) {
    if (res.status === 403) {
      throw new ApiError("Wrong PIN", 403);
    }
    if (res.status === 400) {
      throw new ApiError("Unknown pandal", 400);
    }
    throw new ApiError(`Server error: ${res.statusText}`, res.status);
  }
  return res.json();
}
