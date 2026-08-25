"use client";

import { TableProperties, TrendingUp, Sparkles, Terminal, X, BarChart2 } from "lucide-react";
import { useStore, BottomTab } from "@/lib/store";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { AttributeTable } from "./AttributeTable";
import { ForecastEvalView } from "./ForecastEvalView";
import { ALN2DView } from "./ALN2DView";
import { ConsoleLog } from "./ConsoleLog";
import { DiagnosticsView } from "./DiagnosticsView";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const TABS: { value: BottomTab; label: string; Icon: any; count: (s: any) => string | null }[] = [
  { value: "table",       label: "Attribute Table",       Icon: TableProperties, count: (s) => (s.n > 0 ? String(s.n) : null) },
  { value: "diagnostics", label: "Diagnostics",           Icon: BarChart2,       count: (s) => (s.hasResults ? "4" : null) },
  { value: "forecast",    label: "Forecast Accuracy",     Icon: TrendingUp,      count: (s) => (s.hasForecastEval ? "eval" : null) },
  { value: "aln2d",       label: "2D-ALN Morphodynamics", Icon: Sparkles,        count: (s) => (s.hasAln2d ? "2D" : null) },
  { value: "console",     label: "Console",               Icon: Terminal,        count: (s) => String(s.logs) },
];


export function BottomInspector() {
  const { activeBottomTab, setActiveBottomTab, transects, logs, params, setBottomDockOpen } = useStore();
  const ctx = {
    n: transects?.features?.length || 0,
    hasResults: params?.has_results,
    hasAln2d: params?.has_aln2d_results,
    hasForecastEval: params?.has_forecast_eval,
    logs: logs.length,
  };

  return (
    <Tabs
      value={activeBottomTab}
      onValueChange={(v) => setActiveBottomTab(v as BottomTab)}
      className="gb-panel gap-0 border-t border-slate-200 select-none"
    >
      <div className="flex items-center justify-between border-b border-slate-200 px-2">
        <TabsList className="h-10 w-auto justify-start gap-1 rounded-none border-0 bg-transparent p-0">
          {TABS.map(({ value, label, Icon, count }) => {
            const c = count(ctx);
            return (
              <TabsTrigger
                key={value}
                value={value}
                className="h-10 gap-2 rounded-none border-b-2 border-transparent px-3 text-[13px] font-medium text-slate-500 transition-colors data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-slate-900 data-[state=active]:shadow-none"
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
                {c && (
                  <span
                    className={cn(
                      "rounded-full px-1.5 py-0.5 gb-num text-[10px]",
                      value === "aln2d"
                        ? "bg-emerald-100 text-emerald-700 font-semibold"
                        : value === "diagnostics"
                        ? "bg-sky-100 text-sky-700 font-semibold"
                        : value === "forecast"
                        ? "bg-violet-100 text-violet-700 font-semibold"
                        : "bg-slate-100 text-slate-500"
                    )}
                  >
                    {c}
                  </span>
                )}
              </TabsTrigger>
            );
          })}
        </TabsList>

        <Button size="icon" variant="ghost" className="h-8 w-8 text-slate-400"
          onClick={() => setBottomDockOpen(false)} title="Close dock">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <TabsContent value="table" className="m-0 min-h-0 flex-1 overflow-hidden">
        <AttributeTable />
      </TabsContent>
      <TabsContent value="diagnostics" className="m-0 min-h-0 flex-1 overflow-hidden">
        <DiagnosticsView />
      </TabsContent>
      <TabsContent value="forecast" className="m-0 min-h-0 flex-1 overflow-hidden">
        <ForecastEvalView />
      </TabsContent>
      <TabsContent value="aln2d" className="m-0 min-h-0 flex-1 overflow-hidden">
        <ALN2DView />
      </TabsContent>
      <TabsContent value="console" className="m-0 min-h-0 flex-1 overflow-hidden">
        <ConsoleLog />
      </TabsContent>
    </Tabs>
  );
}
