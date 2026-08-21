// Global client state (zustand). Holds the session id, server params, loaded
// map layers, selected transect, and desktop GIS state.
import { create } from "zustand";
import { toast } from "sonner";
import {
  api,
  ChoroplethResponse,
  FeatureCollection,
  ForecastLayer,
  Params,
} from "./api";

// True when an API error means the backend lost our in-memory session
// (e.g. uvicorn was restarted). Used to transparently re-create one.
const sessionGone = (e: unknown) =>
  e instanceof Error && e.message.toLowerCase().includes("session not found");

// Guards against many concurrent calls all trying to recover at once.
let recovering: Promise<void> | null = null;

export type RibbonTab = "project" | "map" | "analysis" | "forecast" | "view";
export type BottomTab = "table" | "diagnostics" | "console";
export type TableFilterKind = "all" | "eroding" | "accreting" | "changepoints";

export interface LogEntry {
  id: string;
  time: string;
  text: string;
  level: "INFO" | "WARN" | "ERROR" | "SUCCESS";
}

export interface LayerVisibility {
  shorelines: boolean;
  baseline: boolean;
  transects: boolean;
  rates: boolean;
  forecastLine: boolean;
  forecastRibbon: boolean;
}

export interface LayerOpacity {
  shorelines: number;
  baseline: number;
  transects: number;
  rates: number;
  forecast: number;
}

interface ShiftState {
  sessionId: string | null;
  params: Params | null;
  ready: boolean;

  // status & geoprocessing execution
  status: string;
  progress: number;
  running: boolean;
  activeJobName: string | null;
  jobStartTime: number | null;
  logs: LogEntry[];
  isExecutionDrawerOpen: boolean;

  // Desktop GIS Layout Toggles
  activeRibbonTab: RibbonTab;
  tocOpen: boolean;
  inspectorOpen: boolean;
  bottomDockOpen: boolean;
  basemap: string;

  // Live GIS Cursor & Extent
  cursorCoords: { lat: number; lng: number } | null;
  mapZoom: number;

  // Map Layers & Symbology
  shorelines: FeatureCollection | null;
  baseline: FeatureCollection | null;
  transects: FeatureCollection | null;
  choropleth: ChoroplethResponse | null;
  forecast: ForecastLayer | null;
  visibility: LayerVisibility;
  opacity: LayerOpacity;

  // Inspection & Filtering
  selectedTransect: number | null;
  activeBottomTab: BottomTab;
  tableFilter: TableFilterKind;
  tableSearch: string;
  isFieldMappingOpen: boolean;

  // Actions
  init: () => Promise<void>;
  setParam: <K extends keyof Params>(key: K, value: Params[K]) => Promise<void>;
  setStatus: (msg: string, progress?: number) => void;
  setRunning: (v: boolean, jobName?: string) => void;
  log: (msg: string, level?: "INFO" | "WARN" | "ERROR" | "SUCCESS") => void;
  clearLogs: () => void;
  setExecutionDrawerOpen: (v: boolean) => void;
  setFieldMappingOpen: (open: boolean) => void;

  // Layout Setters
  setActiveRibbonTab: (t: RibbonTab) => void;
  setTocOpen: (v: boolean) => void;
  setInspectorOpen: (v: boolean) => void;
  setBottomDockOpen: (v: boolean) => void;
  setBasemap: (v: string) => void;
  setCursorCoords: (coords: { lat: number; lng: number } | null) => void;
  setMapZoom: (z: number) => void;

  // Layer Setters
  setVisibility: (key: keyof LayerVisibility, v: boolean) => void;
  setAllVisibility: (v: boolean) => void;
  setLayerOpacity: (key: keyof LayerOpacity, v: number) => void;

  // Inspection Setters
  setSelectedTransect: (tid: number | null) => void;
  setActiveBottomTab: (t: BottomTab) => void;
  setTableFilter: (f: TableFilterKind) => void;
  setTableSearch: (q: string) => void;

  // Layer Refreshes
  refreshShorelines: () => Promise<void>;
  refreshBaseline: () => Promise<void>;
  refreshTransects: () => Promise<void>;
  refreshResultsLayers: () => Promise<void>;
  reload: () => Promise<void>;
  recoverSession: () => Promise<void>;
}

export const useStore = create<ShiftState>((set, get) => ({
  sessionId: null,
  params: null,
  ready: false,

  status: "Ready — open Map & Layers or Project tab to load data.",
  progress: 0,
  running: false,
  activeJobName: null,
  jobStartTime: null,
  isFieldMappingOpen: false,
  logs: [
    {
      id: "init-1",
      time: new Date().toLocaleTimeString("en-GB"),
      text: "SHIFT Desktop GIS Engine initialized.",
      level: "INFO",
    },
    {
      id: "init-2",
      time: new Date().toLocaleTimeString("en-GB"),
      text: "Coordinate Reference System: EPSG:4326 (WGS 84).",
      level: "INFO",
    },
  ],
  isExecutionDrawerOpen: false,

  activeRibbonTab: "analysis",
  tocOpen: true,
  inspectorOpen: true,
  bottomDockOpen: true,
  basemap: "OpenStreetMap",

  cursorCoords: null,
  mapZoom: 9,

  shorelines: null,
  baseline: null,
  transects: null,
  choropleth: null,
  forecast: null,
  visibility: {
    shorelines: true,
    baseline: true,
    transects: true,
    rates: true,
    forecastLine: true,
    forecastRibbon: true,
  },
  opacity: {
    shorelines: 1.0,
    baseline: 1.0,
    transects: 0.9,
    rates: 0.95,
    forecast: 0.95,
  },

  selectedTransect: null,
  activeBottomTab: "table",
  tableFilter: "all",
  tableSearch: "",

  init: async () => {
    if (get().sessionId) return;
    try {
      const { session_id, params } = await api.createSession();
      set({ sessionId: session_id, params, ready: true });
    } catch (e: any) {
      console.error("Failed to initialize session:", e);
    }
  },

  setParam: async (key, value) => {
    const sid = get().sessionId;
    if (!sid) return;
    set((s) => ({ params: s.params ? { ...s.params, [key]: value } : s.params }));
    try {
      const params = await api.patchParams(sid, { [key]: value } as any);
      set({ params });
    } catch (e) {
      if (sessionGone(e)) return get().recoverSession();
      console.error("Error setting parameter:", e);
    }
  },

  setStatus: (msg, progress) =>
    set((s) => ({ status: msg, progress: progress !== undefined ? progress : s.progress })),

  setRunning: (v, jobName) => {
    set({
      running: v,
      activeJobName: v ? (jobName || "Geoprocessing") : null,
      jobStartTime: v ? Date.now() : null,
    });
  },

  log: (msg, level = "INFO") => {
    const ts = new Date().toLocaleTimeString("en-GB");
    const entry: LogEntry = {
      id: Math.random().toString(36).substring(2, 9),
      time: ts,
      text: msg,
      level,
    };
    set((s) => ({ logs: [...s.logs, entry].slice(-500) }));
  },

  clearLogs: () => set({ logs: [] }),
  setExecutionDrawerOpen: (v) => set({ isExecutionDrawerOpen: v }),
  setFieldMappingOpen: (v) => set({ isFieldMappingOpen: v }),

  setActiveRibbonTab: (t) => set({ activeRibbonTab: t }),
  setTocOpen: (v) => set({ tocOpen: v }),
  setInspectorOpen: (v) => set({ inspectorOpen: v }),
  setBottomDockOpen: (v) => set({ bottomDockOpen: v }),
  setBasemap: (v) => set({ basemap: v }),
  setCursorCoords: (coords) => set({ cursorCoords: coords }),
  setMapZoom: (z) => set({ mapZoom: z }),

  setVisibility: (key, v) =>
    set((s) => ({ visibility: { ...s.visibility, [key]: v } })),

  setAllVisibility: (v) =>
    set((s) => ({
      visibility: {
        shorelines: v,
        baseline: v,
        transects: v,
        rates: v,
        forecastLine: v,
        forecastRibbon: v,
      },
    })),

  setLayerOpacity: (key, v) =>
    set((s) => ({ opacity: { ...s.opacity, [key]: v } })),

  setSelectedTransect: (tid) => set({ selectedTransect: tid }),
  setActiveBottomTab: (t) => set({ activeBottomTab: t }),
  setTableFilter: (f) => set({ tableFilter: f }),
  setTableSearch: (q) => set({ tableSearch: q }),

  refreshShorelines: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    try {
      const shorelines = await api.shorelines(sid);
      set({ shorelines });
    } catch (e) {
      if (sessionGone(e)) return get().recoverSession();
      console.error("Failed to load shorelines layer:", e);
    }
  },

  refreshBaseline: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    try {
      const baseline = await api.baseline(sid);
      set({ baseline });
    } catch (e) {
      if (sessionGone(e)) return get().recoverSession();
      console.error("Failed to load baseline layer:", e);
    }
  },

  refreshTransects: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    try {
      const transects = await api.transects(sid);
      set({ transects });
    } catch (e) {
      if (sessionGone(e)) return get().recoverSession();
      console.error("Failed to load transects layer:", e);
    }
  },

  refreshResultsLayers: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    try {
      const [choropleth, forecast] = await Promise.all([
        api.choropleth(sid).catch(() => null),
        api.forecastLayer(sid).catch(() => null),
      ]);
      set({ choropleth, forecast });
    } catch (e) {
      console.error("Failed to load results layers:", e);
    }
  },

  reload: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    try {
      const params = await api.getParams(sid);
      set({ params });
    } catch (e) {
      if (sessionGone(e)) return get().recoverSession();
      console.error("Failed to reload params:", e);
    }
  },

  // Re-create a fresh backend session after the server lost the old one
  // (e.g. a backend restart). Server-side data is gone, so layers are cleared
  // and the user is asked to reload their inputs.
  recoverSession: async () => {
    if (recovering) return recovering;
    recovering = (async () => {
      try {
        const { session_id, params } = await api.createSession();
        set({
          sessionId: session_id,
          params,
          shorelines: null,
          baseline: null,
          transects: null,
          choropleth: null,
          forecast: null,
          selectedTransect: null,
        });
        get().log("Backend session was reset — reload your data to continue.", "WARN");
        toast.warning("Session was reset by the server. Please reload your data.");
      } catch (e) {
        console.error("Failed to recover session:", e);
      } finally {
        recovering = null;
      }
    })();
    return recovering;
  },
}));
