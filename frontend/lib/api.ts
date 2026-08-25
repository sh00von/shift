// SHIFT API client — talks to the FastAPI backend.
// Empty string = relative URLs (production via reverse proxy).
// Set NEXT_PUBLIC_API_BASE=http://localhost:8437 in .env.local for local dev.
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export interface Params {
  spacing: number;
  smoothing: number;
  transect_length: number;
  cast_side: string;
  buffer_distance: number;
  default_uncertainty: number;
  run_classic: boolean;
  run_ekf: boolean;
  forecast_models: string[];
  has_forecast_eval: boolean;
  aln2d_reach_length?: number;
  aln2d_reach_buffer?: number;
  aln2d_search_mask_buffer?: number;
  scorecard_outlier_z?: number;
  scorecard_tie_pct?: number;
  has_scorecard?: boolean;
  forecast_model: string;
  forecast_horizon: number;
  forecast_ci: number;
  style_metric: string;
  color_ramp: string;
  shoreline_palette: string;
  date_col: string | null;
  date_format: string;
  uncertainty_col: string | null;
  shoreline_filename: string;
  baseline_filename: string;
  has_shoreline: boolean;
  has_baseline: boolean;
  has_results: boolean;
  has_aln2d_results?: boolean;
  logs: string[];
}


export interface ShorelinePreviewRow {
  index: number;
  raw_date: string;
  parsed_date: string;
  parsed_year: number | null;
  raw_uncertainty: string;
  parsed_uncertainty: number;
}

export interface ShorelineFieldsResponse {
  has_shoreline: boolean;
  filename: string;
  columns: string[];
  date_col: string;
  date_format: string;
  uncertainty_col: string | null;
  default_uncertainty: number;
  preview_rows: ShorelinePreviewRow[];
  detected_years: number[];
}

export interface FeatureCollection {
  type: "FeatureCollection";
  features: any[];
}

export interface ChoroplethResponse {
  geojson: FeatureCollection;
  legend: {
    title: string;
    min: number;
    max: number;
    gradient: string;
  } | null;
}

export interface ForecastEvalRow {
  model: string;
  rmse: string;
  mae: string;
  n: number;
}

export interface ForecastEvalView {
  available: boolean;
  rows: ForecastEvalRow[];
  best_model: string | null;
  n_transects: number;
}

export interface CategoricalLayer {
  geojson: FeatureCollection;
  legend: {
    title: string;
    categories: { label: string; color: string; count: number }[];
  } | null;
}

export interface ForecastLayer {
  line: FeatureCollection | null;
  ribbon: FeatureCollection | null;
  target_year: number | null;
  ci_pct: number | null;
  model: string | null;
}

export interface TableRow {
  id: number;
  epr: string;
  lrr: string;
  lrr_ci: string;
  trend: string;
  wlr: string;
  ekf: string;
  sens: string;
  mk_trend: string;
  mk_tau: string;
  mk_p: string;
}


export interface ChartTrace {
  name: string;
  kind: string;
  dash?: string;
  x: number[];
  y: number[];
  color: string;
}

export interface ForecastTrace {
  model: string;
  ci_pct: number;
  years: number[];
  distances: number[];
  lower: number[];
  upper: number[];
  color: string;
}

export interface ChartData {
  transect_id: number;
  summary: string;
  traces: ChartTrace[];
  forecast: ForecastTrace | null;
  forecasts: ForecastTrace[];
}


export interface Aln2dSummaryRow {
  from_epoch: string;
  to_epoch: string;
  span_years: string;
  eroded_km2: string;
  accreted_km2: string;
  erosion_rate_km2_yr: string;
  accretion_rate_km2_yr: string;
  net_balance_km2_yr: string;
}

export interface Aln2dValidationRow {
  metric_name: string;
  vs_lrr: string;
  vs_epr: string;
  vs_kf: string;
}

export interface Aln2dReachRow {
  reach_id: number;
  length_m: string;
  net_2d_m_yr: string;
  ero_2d_m_yr: string;
  acc_2d_m_yr: string;
  dsas_lrr_m_yr: string;
  dsas_epr_m_yr: string;
  dsas_kf_m_yr: string;
}

export const api = {
  createSession: () =>
    fetch(`${API_BASE}/api/session`, { method: "POST" }).then(
      j<{ session_id: string; params: Params }>
    ),

  getParams: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/params`).then(j<Params>),

  patchParams: (sid: string, patch: Partial<Params>) =>
    fetch(`${API_BASE}/api/session/${sid}/params`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }).then(j<Params>),

  clear: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/clear`, { method: "POST" }).then(
      j<Params>
    ),

  uploadShoreline: (sid: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch(`${API_BASE}/api/session/${sid}/upload/shoreline`, {
      method: "POST",
      body: fd,
    }).then(
      j<{
        filename: string;
        n_features: number;
        columns: string[];
        date_col: string;
        uncertainty_col: string | null;
      }>
    );
  },

  getShorelineFields: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/shoreline/fields`).then(
      j<ShorelineFieldsResponse>
    ),

  setShorelineFields: (
    sid: string,
    req: {
      date_col: string;
      date_format: string;
      uncertainty_col?: string | null;
      default_uncertainty: number;
      create_uncertainty_col?: string | null;
    }
  ) =>
    fetch(`${API_BASE}/api/session/${sid}/shoreline/fields`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    }).then(j<ShorelineFieldsResponse>),

  uploadBaseline: (sid: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch(`${API_BASE}/api/session/${sid}/upload/baseline`, {
      method: "POST",
      body: fd,
    }).then(j<{ filename: string; n_features: number }>);
  },

  loadDemo: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/demo`, { method: "POST" }).then(
      j<any>
    ),

  autoBaseline: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/auto-baseline`, {
      method: "POST",
    }).then(j<{ filename: string; n_features: number }>),

  shorelines: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/layers/shorelines`).then(
      j<FeatureCollection>
    ),
  baseline: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/layers/baseline`).then(
      j<FeatureCollection>
    ),
  transects: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/layers/transects`).then(
      j<FeatureCollection>
    ),
  choropleth: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/layers/choropleth`).then(
      j<ChoroplethResponse>
    ),
  forecastLayer: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/layers/forecast`).then(
      j<ForecastLayer>
    ),

  // 2D-ALN Layers & Outputs
  aln2dErosion: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/layers/aln2d/erosion`).then(
      j<FeatureCollection>
    ),
  aln2dAccretion: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/layers/aln2d/accretion`).then(
      j<FeatureCollection>
    ),
  aln2dReaches: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/layers/aln2d/reaches`).then(
      j<ChoroplethResponse>
    ),
  aln2dChange: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/layers/aln2d/change`).then(
      j<ChoroplethResponse>
    ),
  forecastEval: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/forecast/eval`).then(j<ForecastEvalView>),
  aln2dSummary: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/aln2d/summary`).then(
      j<{ rows: Aln2dSummaryRow[] }>
    ),


  aln2dValidation: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/aln2d/validation`).then(
      j<{ rows: Aln2dValidationRow[] }>
    ),
  aln2dReachRows: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/aln2d/reaches`).then(
      j<{ rows: Aln2dReachRow[] }>
    ),

  table: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/table`).then(
      j<{ rows: TableRow[] }>
    ),
  summary: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/summary`).then(j<Record<string, string>>),
  chart: (sid: string, tid: number) =>
    fetch(`${API_BASE}/api/session/${sid}/chart/${tid}`).then(j<ChartData>),
  forecastModels: (sid: string) =>
    fetch(`${API_BASE}/api/session/${sid}/forecast-models`).then(
      j<{ models: string[]; selected: string[] }>
    ),


  exportUrl: (
    sid: string,
    kind: "bundle" | "csv" | "intersections" | "transects" | "transects_rates" | "forecast"
  ) => {
    const map: Record<string, string> = {
      bundle: "export/bundle.zip",
      csv: "export/csv",
      intersections: "export/intersections.csv",
      transects: "export/transects.geojson",
      transects_rates: "export/transects_rates.geojson",
      forecast: "export/forecast.geojson",
    };
    return `${API_BASE}/api/session/${sid}/${map[kind]}`;
  },
};

export type JobKind = "preview" | "analyze" | "forecast" | "aln2d";


export interface ProgressFrame {
  type: "progress" | "done" | "error";
  message?: string;
  progress?: number;
}

// Run a websocket job, invoking onProgress for each frame. Resolves on "done".
export function runJob(
  sid: string,
  kind: JobKind,
  onProgress: (f: ProgressFrame) => void
): Promise<void> {
  const wsBase = API_BASE
    ? API_BASE.replace(/^http/, "ws")
    : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
  const ws = new WebSocket(`${wsBase}/api/session/${sid}/ws/${kind}`);
  return new Promise((resolve, reject) => {
    ws.onmessage = (ev) => {
      const frame: ProgressFrame = JSON.parse(ev.data);
      onProgress(frame);
      if (frame.type === "done") {
        ws.close();
        resolve();
      } else if (frame.type === "error") {
        ws.close();
        reject(new Error(frame.message || "Job failed"));
      }
    };
    ws.onerror = () => reject(new Error("WebSocket connection error"));
    ws.onclose = (ev) => {
      if (ev.code === 4404) reject(new Error("Session expired. Reload the page."));
    };
  });
}
