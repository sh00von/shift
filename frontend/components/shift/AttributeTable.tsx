"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, ArrowUp, ArrowDown, ChevronsUpDown, Download, Package } from "lucide-react";
import { api, TableRow as ApiTableRow } from "@/lib/api";
import { useStore, TableFilterKind } from "@/lib/store";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

const COLS: {
  key: keyof ApiTableRow;
  label: string;
  tooltip?: string;
  align?: "left" | "center" | "right";
  rate?: boolean;
}[] = [
  { key: "id", label: "T-ID", align: "center", tooltip: "Transect ID index" },
  { key: "epr", label: "EPR", align: "right", tooltip: "End Point Rate (m/yr)", rate: true },
  { key: "lrr", label: "LRR", align: "right", tooltip: "Linear Regression Rate (m/yr)", rate: true },
  { key: "tsr", label: "Theil-Sen", align: "right", tooltip: "Robust Median Slope (m/yr)", rate: true },
  { key: "ransac", label: "RANSAC", align: "right", tooltip: "Random Sample Consensus (m/yr)", rate: true },
  { key: "wlr", label: "WLR", align: "right", tooltip: "Weighted Linear Regression (m/yr)", rate: true },
  { key: "bp_rate", label: "Post-break", align: "right", tooltip: "Latest regime rate (m/yr)", rate: true },
  { key: "bp_year", label: "Break yr", align: "center", tooltip: "Inflection / changepoint year" },
  { key: "n_brk", label: "Regimes", align: "center", tooltip: "Number of regime shifts" },
  { key: "rf_rmse", label: "RF RMSE", align: "right", tooltip: "Random Forest residual error (m)" },
];

const FILTERS: { id: TableFilterKind; label: string }[] = [
  { id: "all", label: "All" },
  { id: "eroding", label: "Eroding" },
  { id: "accreting", label: "Accreting" },
  { id: "changepoints", label: "Changepoints" },
];

function rateClass(v: unknown) {
  const n = parseFloat(String(v));
  if (isNaN(n)) return "text-slate-400";
  if (n > 0.05) return "text-emerald-600";
  if (n < -0.05) return "text-rose-600";
  return "text-slate-600";
}

const alignClass = (a?: string) =>
  a === "right" ? "text-right" : a === "center" ? "text-center" : "text-left";

export function AttributeTable() {
  const {
    sessionId,
    params,
    selectedTransect,
    setSelectedTransect,
    setInspectorOpen,
    tableFilter,
    setTableFilter,
    tableSearch,
    setTableSearch,
  } = useStore();

  const [rows, setRows] = useState<ApiTableRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [sort, setSort] = useState<{ key: keyof ApiTableRow; dir: 1 | -1 } | null>(null);

  useEffect(() => {
    if (params?.has_results && sessionId) {
      setLoading(true);
      api.table(sessionId).then((r) => setRows(r.rows)).catch(() => setRows([])).finally(() => setLoading(false));
    } else {
      setRows([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params?.has_results, sessionId]);

  const filtered = useMemo(() => {
    let out = rows;
    if (tableFilter === "eroding")
      out = out.filter((r) => { const v = parseFloat(String(r.lrr ?? r.epr ?? "0")); return !isNaN(v) && v < 0; });
    else if (tableFilter === "accreting")
      out = out.filter((r) => { const v = parseFloat(String(r.lrr ?? r.epr ?? "0")); return !isNaN(v) && v > 0; });
    else if (tableFilter === "changepoints")
      out = out.filter((r) => { const n = parseInt(String(r.n_brk ?? "0")); return !isNaN(n) && n > 1; });

    const q = tableSearch.trim().toLowerCase();
    if (q) out = out.filter((r) => Object.values(r).some((v) => String(v).toLowerCase().includes(q)));

    if (sort) {
      out = [...out].sort((a, b) => {
        const av = parseFloat(String(a[sort.key] ?? "")); const bv = parseFloat(String(b[sort.key] ?? ""));
        const an = isNaN(av), bn = isNaN(bv);
        if (an && bn) return 0;
        if (an) return 1;
        if (bn) return -1;
        return (av - bv) * sort.dir;
      });
    }
    return out;
  }, [rows, tableFilter, tableSearch, sort]);

  const toggleSort = (key: keyof ApiTableRow) =>
    setSort((s) => (s?.key === key ? { key, dir: (s.dir * -1) as 1 | -1 } : { key, dir: 1 }));

  const onRowClick = (tid: number) => {
    setSelectedTransect(tid);
    setInspectorOpen(true);
  };

  return (
    <div className="gb-panel">
      {/* Toolbar */}
      <div className="flex flex-shrink-0 flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-3 py-2">
        <div className="flex items-center gap-3">
          <span className="text-[13px] text-slate-500">
            <span className="font-semibold text-slate-800">
              {tableSearch || tableFilter !== "all" ? filtered.length : rows.length}
            </span>{" "}
            {tableSearch || tableFilter !== "all" ? `of ${rows.length} ` : ""}transects
          </span>

          {/* Segmented filter */}
          <div className="hidden items-center gap-0.5 rounded-lg bg-slate-100 p-0.5 sm:flex">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                onClick={() => setTableFilter(f.id)}
                className={cn(
                  "rounded-md px-2.5 py-1 text-[12px] font-medium transition-colors",
                  tableFilter === f.id
                    ? "bg-white text-slate-900 shadow-sm ring-1 ring-slate-200"
                    : "text-slate-500 hover:text-slate-800"
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            <Input
              value={tableSearch}
              onChange={(e) => setTableSearch(e.target.value)}
              placeholder="Search…"
              className="h-9 w-56 pl-8 text-sm"
            />
          </div>
          <Button size="sm" variant="outline" className="h-9 gap-1.5 font-medium"
            onClick={() => sessionId && window.open(api.exportUrl(sessionId, "csv"), "_blank")}
            disabled={!rows.length}>
            <Download className="h-4 w-4 text-slate-500" /> CSV
          </Button>
          <Button size="sm" variant="outline" className="h-9 gap-1.5 font-medium text-sky-700 bg-sky-50/50 border-sky-200 hover:bg-sky-100"
            onClick={() => sessionId && window.open(api.exportUrl(sessionId, "bundle"), "_blank")}
            disabled={!rows.length}>
            <Package className="h-4 w-4 text-sky-600" /> GIS Package (.ZIP)
          </Button>
        </div>
      </div>

      {/* Grid */}
      <div className="shift-scroll flex-1 overflow-auto">
        <Table className="w-full">
          <TableHeader className="sticky top-0 z-10 bg-slate-50/95 backdrop-blur-sm">
            <TableRow className="border-slate-200 hover:bg-transparent">
              {COLS.map((c) => (
                <TableHead
                  key={c.key}
                  onClick={() => toggleSort(c.key)}
                  title={c.tooltip}
                  className={cn(
                    "h-9 cursor-pointer select-none px-3 text-[12px] font-semibold text-slate-500 transition-colors hover:text-slate-800",
                    alignClass(c.align)
                  )}
                >
                  <span className={cn("inline-flex items-center gap-1",
                    c.align === "right" ? "flex-row-reverse" : "")}>
                    {c.label}
                    {sort?.key === c.key ? (
                      sort.dir === 1 ? <ArrowUp className="h-3 w-3 text-primary" /> : <ArrowDown className="h-3 w-3 text-primary" />
                    ) : (
                      <ChevronsUpDown className="h-3 w-3 text-slate-300" />
                    )}
                  </span>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={COLS.length} className="h-32 text-center text-[13px] text-slate-400">
                  {loading
                    ? "Loading transect attributes…"
                    : rows.length === 0
                    ? "No results yet — run an analysis to populate the table."
                    : "No transects match the active filters."}
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((r) => {
                const isSel = selectedTransect === r.id;
                return (
                  <TableRow
                    key={r.id}
                    onClick={() => onRowClick(r.id)}
                    className={cn(
                      "cursor-pointer border-slate-100 transition-colors",
                      isSel ? "bg-primary/5 hover:bg-primary/10" : "hover:bg-slate-50"
                    )}
                  >
                    {COLS.map((c) => (
                      <TableCell
                        key={c.key}
                        className={cn(
                          "gb-num px-3 py-2 text-[13px]",
                          alignClass(c.align),
                          c.key === "id"
                            ? cn("font-semibold", isSel ? "text-primary" : "text-slate-700")
                            : c.rate
                            ? rateClass(r[c.key])
                            : "text-slate-600"
                        )}
                      >
                        {r[c.key] ?? "—"}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
