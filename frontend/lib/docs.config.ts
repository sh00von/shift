// Documentation navigation manifest.
// A single source of truth consumed by the sidebar (DocsSidebar) and by the
// catch-all route's generateStaticParams(). To add a page: drop a matching
// markdown file under content/docs/<slug>.md and add one entry here.

export interface DocPage {
  /** URL slug relative to /docs (also the markdown path under content/docs). */
  slug: string;
  /** Sidebar + <title> label. */
  title: string;
}

export interface DocSection {
  title: string;
  pages: DocPage[];
}

export const DOCS_NAV: DocSection[] = [
  {
    title: "Getting Started",
    pages: [
      { slug: "", title: "Overview" },
      { slug: "getting-started", title: "Installation & First Run" },
      { slug: "data-requirements", title: "Data Requirements" },
    ],
  },
  {
    title: "User Guide",
    pages: [
      { slug: "guide/upload-data", title: "Loading Data" },
      { slug: "guide/field-mapping", title: "Field Mapping" },
      { slug: "guide/cast-transects", title: "Casting Transects" },
      { slug: "guide/run-analysis", title: "Running Rate Analysis" },
      { slug: "guide/inspect-transects", title: "Inspecting Transects" },
      { slug: "guide/rank-methods", title: "Ranking Methods" },
      { slug: "guide/2d-aln", title: "2D-ALN Engine" },
      { slug: "guide/forecast", title: "Forecasting" },
      { slug: "guide/map-and-layers", title: "Map & Layers" },
      { slug: "guide/bottom-inspector", title: "Bottom Inspector" },
      { slug: "guide/export", title: "Exporting Results" },
    ],
  },
  {
    title: "Methods Reference",
    pages: [
      { slug: "methods/dsas-classic", title: "DSAS Classic (EPR/LRR/WLR/NSM/SCE)" },
      { slug: "methods/ekf", title: "Extended Kalman Filter (EKF)" },
      { slug: "methods/forecast-models", title: "Forecast Models" },
      { slug: "methods/2d-aln", title: "2D-ALN Method & Lineage" },
      { slug: "methods/scorecard", title: "Model Scorecard (Cross-Validation)" },
    ],
  },
  {
    title: "Technical Reference",
    pages: [
      { slug: "reference/architecture", title: "Architecture" },
      { slug: "reference/rest-api", title: "REST API" },
      { slug: "reference/websockets", title: "WebSocket Jobs" },
      { slug: "reference/parameters", title: "Parameters" },
      { slug: "reference/export-artifacts", title: "Export Artifacts" },
      { slug: "reference/data-models", title: "Data Models" },
    ],
  },
];

/** Flattened, ordered list of every page (used for prev/next + static params). */
export const DOCS_FLAT: DocPage[] = DOCS_NAV.flatMap((s) => s.pages);
