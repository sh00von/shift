"use client";

import { useEffect, useRef, Fragment } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { useStore } from "@/lib/store";

const BASEMAPS: Record<string, { url: string; attr: string }> = {
  OpenStreetMap: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr: "&copy; OpenStreetMap contributors",
  },
  "Esri World Imagery": {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr: "Tiles &copy; Esri, Maxar, Earthstar Geographics",
  },
  "Carto Light": {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attr: "&copy; OpenStreetMap &copy; CARTO",
  },
};

function MapController() {
  const map = useMap();
  const {
    shorelines,
    baseline,
    transects,
    choropleth,
    selectedTransect,
    setCursorCoords,
    setMapZoom,
  } = useStore();

  const highlightLayerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    (window as any).__shiftMap = map;
    setMapZoom(map.getZoom());
  }, [map, setMapZoom]);

  useMapEvents({
    mousemove(e) {
      setCursorCoords({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
    mouseout() {
      setCursorCoords(null);
    },
    zoomend() {
      setMapZoom(map.getZoom());
    },
  });

  // Fit bounds when layers load
  useEffect(() => {
    const fcs = [shorelines, baseline, transects, choropleth?.geojson].filter(
      Boolean
    ) as any[];
    const layers = fcs.flatMap((fc) => fc.features);
    if (!layers.length) return;
    try {
      const gj = L.geoJSON({ type: "FeatureCollection", features: layers } as any);
      const b = gj.getBounds();
      if (b.isValid()) {
        (window as any).__shiftBounds = b;
        map.fitBounds(b, { padding: [35, 35] });
      }
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shorelines, baseline, transects, choropleth]);

  // Highlight selected transect
  useEffect(() => {
    if (!highlightLayerRef.current) {
      highlightLayerRef.current = L.layerGroup().addTo(map);
    }
    highlightLayerRef.current.clearLayers();

    if (selectedTransect === null) return;

    const sourceFeatures =
      choropleth?.geojson?.features || transects?.features || [];
    const target = sourceFeatures.find(
      (f: any) =>
        f.properties?.transect_id === selectedTransect || f.properties?.id === selectedTransect
    );

    if (target) {
      const gjLayer = L.geoJSON(target as any, {
        style: {
          color: "#0284c7",
          weight: 6,
          opacity: 0.95,
          dashArray: undefined,
        },
      });
      gjLayer.addTo(highlightLayerRef.current);
    }
  }, [selectedTransect, choropleth, transects, map]);

  return null;
}

export default function MapCanvas({ basemap }: { basemap: string }) {
  const {
    shorelines,
    baseline,
    transects,
    choropleth,
    forecast,
    aln2dChange,
    aln2dReaches,
    bestMethod,
    groupOrder,
    layerOrderByGroup,
    visibility,
    opacity,
    selectedTransect,
    setSelectedTransect,
    setInspectorOpen,
  } = useStore();

  const bm = BASEMAPS[basemap] ?? BASEMAPS.OpenStreetMap;

  const onTransectClick = (tid: number) => {
    setSelectedTransect(tid);
    setInspectorOpen(true);
  };

  // One render node per layer id — the panel decides the order.
  const layerNodes: Record<string, React.ReactNode> = {
    shorelines: visibility.shorelines && shorelines ? (
      <GeoJSON
        key={`sl-${shorelines.features.length}-${opacity.shorelines}-${(shorelines.features[0] as any)?.properties?.color ?? ""}`}
        data={shorelines as any}
        style={(f: any) => ({ color: f.properties?.color || "#0284c7", weight: 2.5, opacity: opacity.shorelines })}
        onEachFeature={(f, layer) => {
          if (f.properties?.date_str) {
            layer.bindTooltip(`<div class="font-sans text-xs"><b>Survey Epoch:</b> ${f.properties.date_str}</div>`, { sticky: true });
          }
        }}
      />
    ) : null,

    baseline: visibility.baseline && baseline ? (
      <GeoJSON
        key={`bl-${baseline.features.length}-${opacity.baseline}`}
        data={baseline as any}
        style={{ color: "#ea580c", weight: 3, opacity: opacity.baseline, dashArray: "6 5" }}
        onEachFeature={(_f, layer) => {
          layer.bindTooltip(`<div class="font-sans text-xs"><b>Baseline Reference Line</b></div>`, { sticky: true });
        }}
      />
    ) : null,

    transects: visibility.transects && transects ? (
      <GeoJSON
        key={`tr-${transects.features.length}-${opacity.transects}-${(transects.features[0] as any)?.geometry?.coordinates?.[1]?.[0] ?? ""}-${(transects.features[0] as any)?.properties?.cast_side ?? ""}`}
        data={transects as any}
        style={{ color: "#3b82f6", weight: 2, opacity: opacity.transects }}
        onEachFeature={(f, layer) => {
          const tid = f.properties?.transect_id;
          if (tid !== undefined) {
            layer.bindTooltip(`<div class="font-sans text-xs"><b>Transect #${tid}</b></div>`, { sticky: true });
            layer.on("click", () => onTransectClick(tid));
          }
        }}
      />
    ) : null,

    rates: visibility.rates && choropleth?.geojson?.features?.length ? (
      <GeoJSON
        key={`rl-${choropleth.geojson.features.length}-${choropleth.legend?.title}-${choropleth.legend?.min}-${choropleth.legend?.max}-${opacity.rates}-${(choropleth.geojson.features[0] as any)?.properties?.color ?? ""}`}
        data={choropleth.geojson as any}
        style={(f: any) => {
          const isSelected = f.properties?.transect_id === selectedTransect;
          return { color: f.properties?.color || "#16a34a", weight: isSelected ? 5.5 : 3.5, opacity: isSelected ? 1 : opacity.rates };
        }}
        onEachFeature={(f, layer) => {
          const p = f.properties;
          layer.bindTooltip(
            `<div class="font-sans text-xs space-y-0.5">
              <div class="font-bold text-slate-900">Transect #${p.transect_id}</div>
              <div class="font-mono text-emerald-700 font-semibold">${p.label || "Rate Calculated"}</div>
            </div>`,
            { sticky: true }
          );
          layer.on("click", () => onTransectClick(p.transect_id));
        }}
      />
    ) : null,

    forecast: (
      <>
        {visibility.forecastRibbon && forecast?.ribbon && (
          <GeoJSON
            key={`fcr-${forecast.target_year}-${forecast.model}-${opacity.forecast}`}
            data={forecast.ribbon as any}
            style={{ color: "#9333ea", weight: 1.5, fillColor: "#a855f7", fillOpacity: 0.22, dashArray: "3 4" }}
          />
        )}
        {visibility.forecastLine && forecast?.line && (
          <GeoJSON
            key={`fcl-${forecast.target_year}-${forecast.model}-${opacity.forecast}-${(forecast.line.features[0] as any)?.geometry?.coordinates?.[0]?.[0] ?? ""}`}
            data={forecast.line as any}
            style={{ color: "#9333ea", weight: 3.5, opacity: opacity.forecast, dashArray: "6 4" }}
            onEachFeature={(_f, layer) =>
              layer.bindTooltip(
                `<div class="font-sans text-xs space-y-0.5">
                  <div class="font-bold text-purple-900">🔮 Forecast Shoreline (${forecast.target_year})</div>
                  <div class="text-[11px] text-purple-700 font-mono">${forecast.model} (${forecast.ci_pct}% CI)</div>
                </div>`,
                { sticky: true }
              )
            }
          />
        )}
      </>
    ),

    aln2d_change: visibility.aln2dChange && aln2dChange?.geojson?.features?.length ? (
      <GeoJSON
        key={`aln2d-chg-${aln2dChange.geojson.features.length}-${opacity.aln2dChange}-${aln2dChange.legend?.max ?? ""}`}
        data={aln2dChange.geojson as any}
        style={(f: any) => ({ color: f.properties?.color || "#94a3b8", weight: 1, fillColor: f.properties?.color || "#94a3b8", fillOpacity: opacity.aln2dChange * 0.6 })}
        onEachFeature={(f, layer) => {
          const p = f.properties;
          const isEro = p.change_type === "Erosion";
          layer.bindTooltip(
            `<div class="font-sans text-xs space-y-0.5">
              <div class="font-bold ${isEro ? "text-red-700" : "text-emerald-700"}">${isEro ? "🔴" : "🟢"} 2D-ALN ${p.change_type || "Change"}</div>
              <div class="text-[11px] text-slate-700">Period: ${p.period || "Epoch Transition"}</div>
              <div class="text-[11px] font-mono font-semibold ${isEro ? "text-red-600" : "text-emerald-600"}">${p.signed_rate_km2_yr > 0 ? "+" : ""}${p.signed_rate_km2_yr ?? "—"} km²/yr</div>
            </div>`,
            { sticky: true }
          );
        }}
      />
    ) : null,

    best_method: visibility.bestMethod && bestMethod?.geojson?.features?.length ? (
      <GeoJSON
        key={`best-${bestMethod.geojson.features.length}-${opacity.bestMethod}`}
        data={bestMethod.geojson as any}
        style={(f: any) => ({ color: f.properties?.color || "#94a3b8", weight: 3, opacity: opacity.bestMethod })}
        onEachFeature={(f, layer) => {
          const p = f.properties;
          layer.bindTooltip(
            `<div class="font-sans text-xs space-y-0.5">
              <div class="font-bold text-slate-900">Transect #${p.transect_id}</div>
              <div class="font-mono font-semibold" style="color:${p.color}">Best: ${p.winner}</div>
            </div>`,
            { sticky: true }
          );
        }}
      />
    ) : null,

    aln2d_reaches: visibility.aln2dReaches && aln2dReaches?.geojson?.features?.length ? (
      <GeoJSON
        key={`aln2d-rch-${aln2dReaches.geojson.features.length}-${opacity.aln2dReaches}`}
        data={aln2dReaches.geojson as any}
        style={(f: any) => ({ color: f.properties?.color || "#059669", weight: 4.5, opacity: opacity.aln2dReaches })}
        onEachFeature={(f, layer) => {
          const p = f.properties;
          layer.bindTooltip(
            `<div class="font-sans text-xs space-y-1">
              <div class="font-bold text-slate-900">Reach #${p.reach_id} (${p.length_m} m)</div>
              <div class="font-mono text-xs font-semibold ${p.net_2d_m_yr >= 0 ? "text-emerald-700" : "text-red-700"}">
                2D-ALN Rate: ${p.net_2d_m_yr > 0 ? "+" : ""}${p.net_2d_m_yr} m/yr
              </div>
            </div>`,
            { sticky: true }
          );
        }}
      />
    ) : null,
  };

  // Panel top→bottom = map top→bottom. Leaflet paints later-added on top,
  // so render the flattened panel order reversed (bottom of panel first).
  const flat: string[] = [];
  groupOrder.forEach((g) => (layerOrderByGroup[g] || []).forEach((id) => flat.push(id)));
  const renderOrder = [...flat].reverse();

  return (
    <MapContainer center={[22.5, 90.6]} zoom={9} className="h-full w-full" preferCanvas>
      <TileLayer url={bm.url} attribution={bm.attr} />
      <MapController />
      {renderOrder.map((id) => (
        <Fragment key={id}>{layerNodes[id] ?? null}</Fragment>
      ))}
    </MapContainer>
  );
}

