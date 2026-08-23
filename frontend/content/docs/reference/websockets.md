# WebSocket Jobs

Long-running analysis runs over WebSockets so the UI can show live, staged progress. Each job
executes a blocking `pipeline` function in a worker thread (`asyncio.to_thread`) and streams
frames back.

## Endpoints

Base: `ws://localhost:8000`. `{sid}` is the session id.

| Endpoint | Job | Pipeline function |
|---|---|---|
| `/api/session/{sid}/ws/preview` | Cast transects only | `preview_transects` |
| `/api/session/{sid}/ws/analyze` | Full rate analysis (all enabled methods) | `run_analysis` |
| `/api/session/{sid}/ws/aln2d` | 2D-ALN morphodynamic analysis | `run_aln2d` |
| `/api/session/{sid}/ws/scorecard` | Cross-validation ranking | `run_scorecard` |
| `/api/session/{sid}/ws/forecast` | Forward projection | `generate_forecast` |

## Frame schema

Every message the server sends is a progress frame:

```ts
type ProgressFrame = {
  type: "progress" | "done" | "error";
  message?: string;   // human-readable status
  progress?: number;  // 0.0 – 1.0
};
```

- `progress` frames stream throughout the job; the frontend updates the status bar, the
  progress modal, and the console log.
- `done` signals successful completion — the client then re-fetches the relevant layers and
  tables.
- `error` carries a failure message.

## Client usage

The frontend wraps this in `runJob(sessionId, kind, onFrame)` (`lib/api.ts`). Typical stages
surfaced to the user:

- **analyze:** ingest → transects → intersect → models → forecast.
- **aln2d:** ingest & CRS → topology mask → 2D Boolean → reach normalization → complete.

Jobs that aren't streamed (upload, demo, auto-baseline) are ordinary REST calls shown with an
indeterminate progress indicator.
