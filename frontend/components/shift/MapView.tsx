"use client";

import dynamic from "next/dynamic";
import { Maximize2, Crosshair, X } from "lucide-react";
import { useStore } from "@/lib/store";
import { Button } from "@/components/ui/button";

const MapCanvas = dynamic(() => import("./MapCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-slate-100 text-sm text-slate-400">
      Loading map…
    </div>
  ),
});

export function MapView() {
  const { basemap, choropleth, selectedTransect, setSelectedTransect, transects } = useStore();

  const zoomToFull = () => {
    if ((window as any).__shiftMap && (window as any).__shiftBounds) {
      (window as any).__shiftMap.fitBounds((window as any).__shiftBounds, { padding: [35, 35] });
    }
  };

  const zoomToSelected = () => {
    if (selectedTransect === null || !(window as any).__shiftMap) return;
    const feats = choropleth?.geojson?.features || transects?.features || [];
    const feat = feats.find(
      (f: any) => f.properties?.transect_id === selectedTransect || f.properties?.id === selectedTransect
    );
    const coords = feat?.geometry?.coordinates;
    if (coords && coords.length >= 2) {
      const p1 = coords[0];
      const p2 = coords[coords.length - 1];
      (window as any).__shiftMap.fitBounds([[p1[1], p1[0]], [p2[1], p2[0]]], { padding: [50, 50], maxZoom: 14 });
    }
  };

  return (
    <div className="relative h-full w-full overflow-hidden bg-slate-100 select-none">
      <MapCanvas basemap={basemap} />

      {/* Navigation tools (top-right) */}
      <div className="gb-surface absolute right-3 top-3 z-[500] flex flex-col gap-0.5 p-1">
        <Button size="icon" variant="ghost" className="h-8 w-8 text-slate-600"
          onClick={zoomToFull} title="Zoom to full extent">
          <Maximize2 className="h-4 w-4" />
        </Button>
        {selectedTransect !== null && (
          <>
            <div className="mx-1 h-px bg-slate-200" />
            <Button size="icon" variant="ghost" className="h-8 w-8 text-primary"
              onClick={zoomToSelected} title={`Zoom to transect #${selectedTransect}`}>
              <Crosshair className="h-4 w-4" />
            </Button>
            <Button size="icon" variant="ghost" className="h-8 w-8 text-slate-500"
              onClick={() => setSelectedTransect(null)} title="Clear selection">
              <X className="h-4 w-4" />
            </Button>
          </>
        )}
      </div>

      {/* Legend (bottom-left) */}
      {choropleth?.legend && (
        <div className="gb-surface absolute bottom-3 left-3 z-[500] w-60 p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-[12px] font-medium text-slate-700">{choropleth.legend.title}</span>
            <span className="text-[11px] text-slate-400">m/yr</span>
          </div>
          <div className="h-2.5 w-full rounded-sm border border-slate-200" style={{ background: choropleth.legend.gradient }} />
          <div className="mt-1.5 flex justify-between gb-num text-[11px] text-slate-500">
            <span>{choropleth.legend.min.toFixed(1)}</span>
            <span>0.0</span>
            <span>+{choropleth.legend.max.toFixed(1)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
