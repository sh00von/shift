// Global client state (zustand). Holds the session id, server params, loaded
// map layers, selected transect, and desktop GIS state.
import { create } from "zustand";
import { toast } from "sonner";
import {
  api,
  ChoroplethResponse,
  FeatureCollection,
  ForecastLayer,
  ForecastEvalView,
  Params,
} from "./api";

// True when an API error means the backend lost our in-memory session
// (e.g. uvicorn was restarted). Used to transparently re-create one.
const sessionGone = (e: unknown) =>
  e instanceof Error && e.message.toLowerCase().includes("session not found");

// Guards against many concurrent calls all trying to recover at once.
let recovering: Promise<void> | null = null;

export type RibbonTab = "project" | "map" | "analysis" | "forecast" | "view";
export type BottomTab = "table" | "forecast" | "aln2d" | "console";
export type TableFilterKind = "all" | "eroding" | "accreting";

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
  aln2dChange: boolean;
  aln2dReaches: boolean;
}

export interface LayerOpacity {
  shorelines: number;
  baseline: number;
  transects: number;
  rates: number;
  forecast: number;
  aln2dChange: number;
  aln2dReaches: number;
}

// ── QGIS-style layer tree: fixed groups + user-reorderable draw order ──
export type LayerGroupId = "comparison" | "transects_rates" | "inputs" | "aln2d";

export interface LayerGroupDef {
  id: LayerGroupId;
  label: string;
}

export const LAYER_GROUPS: LayerGroupDef[] = [
  { id: "comparison", label: "Method Comparison" },
  { id: "transects_rates", label: "Transects & Rates" },
  { id: "inputs", label: "Inputs" },
  { id: "aln2d", label: "2D-ALN" },
];

// Default group order (top of panel = drawn on top of map) and per-group layer order.
export const DEFAULT_GROUP_ORDER: LayerGroupId[] = ["transects_rates", "inputs", "aln2d"];
export const DEFAULT_LAYER_ORDER: Record<LayerGroupId, string[]> = {
  comparison: [],
  transects_rates: ["forecast", "rates", "transects"],
  inputs: ["shorelines", "baseline"],
  aln2d: ["aln2d_reaches", "aln2d_change"],
};

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

  // 2D-ALN Engine Layers & Data
  aln2dChange: ChoroplethResponse | null;
  aln2dReaches: ChoroplethResponse | null;
  forecastEval: ForecastEvalView | null;
  aln2dSummary: any[] | null;
  aln2dValidation: any[] | null;
  aln2dReachRows: any[] | null;

  visibility: LayerVisibility;
  opacity: LayerOpacity;

  // QGIS-style layer tree ordering (session-only)
  groupOrder: LayerGroupId[];
  layerOrderByGroup: Record<LayerGroupId, string[]>;
  collapsedGroups: LayerGroupId[];


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

  // QGIS-style layer tree actions
  reorderLayerInGroup: (group: LayerGroupId, fromId: string, toId: string) => void;
  moveLayerToEdge: (group: LayerGroupId, layerId: string, edge: "top" | "bottom") => void;
  reorderGroups: (fromId: LayerGroupId, toId: LayerGroupId) => void;
  toggleGroupCollapse: (group: LayerGroupId) => void;
  resetLayerOrder: () => void;

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
  refreshAln2d: () => Promise<void>;
  refreshForecastEval: () => Promise<void>;
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

  aln2dChange: null,
  aln2dReaches: null,
  forecastEval: null,
  aln2dSummary: null,
  aln2dValidation: null,
  aln2dReachRows: null,

  visibility: {
    shorelines: true,
    baseline: true,
    transects: true,
    rates: true,
    forecastLine: true,
    forecastRibbon: true,
    aln2dChange: true,
    aln2dReaches: true,
  },
  opacity: {
    shorelines: 1.0,
    baseline: 1.0,
    transects: 0.9,
    rates: 0.95,
    forecast: 0.95,
    aln2dChange: 0.7,
    aln2dReaches: 0.95,
  },


  groupOrder: [...DEFAULT_GROUP_ORDER],
  layerOrderByGroup: {
    comparison: [...DEFAULT_LAYER_ORDER.comparison],
    transects_rates: [...DEFAULT_LAYER_ORDER.transects_rates],
    inputs: [...DEFAULT_LAYER_ORDER.inputs],
    aln2d: [...DEFAULT_LAYER_ORDER.aln2d],
  },
  collapsedGroups: [],


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
      visibility: (Object.fromEntries(
        Object.keys(s.visibility).map((k) => [k, v])
      ) as unknown) as LayerVisibility,
    })),


  setLayerOpacity: (key, v) =>
    set((s) => ({ opacity: { ...s.opacity, [key]: v } })),

  reorderLayerInGroup: (group, fromId, toId) =>
    set((s) => {
      if (fromId === toId) return {};
      const arr = [...s.layerOrderByGroup[group]];
      const from = arr.indexOf(fromId);
      const to = arr.indexOf(toId);
      if (from < 0 || to < 0) return {};
      arr.splice(from, 1);
      arr.splice(arr.indexOf(toId) + (to > from ? 1 : 0), 0, fromId);
      return { layerOrderByGroup: { ...s.layerOrderByGroup, [group]: arr } };
    }),

  moveLayerToEdge: (group, layerId, edge) =>
    set((s) => {
      const arr = s.layerOrderByGroup[group].filter((id) => id !== layerId);
      if (arr.length === s.layerOrderByGroup[group].length) return {};
      if (edge === "top") arr.unshift(layerId);
      else arr.push(layerId);
      return { layerOrderByGroup: { ...s.layerOrderByGroup, [group]: arr } };
    }),

  reorderGroups: (fromId, toId) =>
    set((s) => {
      if (fromId === toId) return {};
      const arr = [...s.groupOrder];
      const from = arr.indexOf(fromId);
      const to = arr.indexOf(toId);
      if (from < 0 || to < 0) return {};
      arr.splice(from, 1);
      arr.splice(arr.indexOf(toId) + (to > from ? 1 : 0), 0, fromId);
      return { groupOrder: arr };
    }),

  toggleGroupCollapse: (group) =>
    set((s) => ({
      collapsedGroups: s.collapsedGroups.includes(group)
        ? s.collapsedGroups.filter((g) => g !== group)
        : [...s.collapsedGroups, group],
    })),

  resetLayerOrder: () =>
    set({
      groupOrder: [...DEFAULT_GROUP_ORDER],
      layerOrderByGroup: {
        comparison: [...DEFAULT_LAYER_ORDER.comparison],
        transects_rates: [...DEFAULT_LAYER_ORDER.transects_rates],
        inputs: [...DEFAULT_LAYER_ORDER.inputs],
        aln2d: [...DEFAULT_LAYER_ORDER.aln2d],
      },
      collapsedGroups: [],
    }),

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

  refreshAln2d: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    try {
      const [change, reaches, summaryRes, valRes, reachRowsRes] = await Promise.all([
        api.aln2dChange(sid).catch(() => null),
        api.aln2dReaches(sid).catch(() => null),
        api.aln2dSummary(sid).catch(() => ({ rows: [] })),
        api.aln2dValidation(sid).catch(() => ({ rows: [] })),
        api.aln2dReachRows(sid).catch(() => ({ rows: [] })),
      ]);
      set({
        aln2dChange: change,
        aln2dReaches: reaches,
        aln2dSummary: summaryRes?.rows || [],
        aln2dValidation: valRes?.rows || [],
        aln2dReachRows: reachRowsRes?.rows || [],
      });
    } catch (e) {
      console.error("Failed to refresh 2D-ALN layers:", e);
    }
  },

  refreshForecastEval: async () => {
    const sid = get().sessionId;
    if (!sid) return;
    try {
      const ev = await api.forecastEval(sid).catch(() => null);
      set({ forecastEval: ev });
    } catch (e) {
      console.error("Failed to refresh forecast eval:", e);
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
