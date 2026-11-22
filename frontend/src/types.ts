export type ZoneLevel = "GREEN" | "AMBER" | "RED" | "CHECK";

export interface Zone {
  id: number;
  count: number;
  density: number;
  level: ZoneLevel;
}

export type AlertLevel = "RED" | "CHECK" | "PUBLIC" | "ADMIN";

export interface Alert {
  clock: string;
  zone: number | null;
  level: AlertLevel;
  message: string;
  action: string;
}

export type SiteStatus = "CLEAR" | "BUSY" | "VERY BUSY" | "CLOSED";

export interface Site {
  id: string;
  name: string;
  live: boolean;
  closed: boolean;
  people: number;
  capacity: number;
  occupancy: number;
  status: SiteStatus;
}

export interface PublicSite {
  id: string;
  name: string;
  status: string;
}

export interface PublicSitesResponse {
  gates: string[];
  sites: PublicSite[];
}

export interface Advisory {
  clock: string;
  gate: string;
  want: string;
  send: string;
  redirected: boolean;
}

export interface AppState {
  ready: boolean;
  calibrated: boolean;
  video_time: number;
  clock: string;
  everyone: number;
  inside: number;
  zones: Zone[];
  alerts: Alert[];
  history: number[];
  sites: Site[];
  advisories: Advisory[];
}

export interface RecommendationResponse {
  send: string | null;
  send_name: string | null;
  redirected: boolean;
  status: string | null;
  minutes: number | null;
  message: string;
}

export interface AdminClosedRequest {
  site: string;
  closed: boolean;
  pin: string;
}

export interface AdminClosedResponse {
  site: string;
  closed: boolean;
}
