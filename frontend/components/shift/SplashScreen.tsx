"use client";

import React, { useEffect, useState } from "react";
import { Compass, Waves, Layers, Globe } from "lucide-react";

const INIT_STEPS = [
  "Initializing SHIFT Desktop GIS Engine…",
  "Mounting Leaflet Canvas & WebGL Spatial Shaders…",
  "Loading USGS DSAS Engine (EPR, LRR, WLR, NSM, SCE)…",
  "Preparing Breakpoint Regime-Shift & Robust Regressors…",
  "Connecting Realtime Geoprocessing Pipeline…",
];

export function SplashScreen() {
  const [stepIdx, setStepIdx] = useState(0);
  const [progress, setProgress] = useState(15);

  useEffect(() => {
    const stepInterval = setInterval(() => {
      setStepIdx((prev) => (prev + 1) % INIT_STEPS.length);
    }, 1100);

    const progressInterval = setInterval(() => {
      setProgress((prev) => (prev >= 92 ? 92 : prev + Math.floor(Math.random() * 12) + 6));
    }, 400);

    return () => {
      clearInterval(stepInterval);
      clearInterval(progressInterval);
    };
  }, []);

  return (
    <div className="relative flex h-screen w-screen flex-col items-center justify-center overflow-hidden bg-gradient-to-b from-slate-50 via-slate-50 to-sky-50/30 text-slate-800 select-none">
      {/* Background Subtle Grid Pattern */}
      <div 
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, #0f172a 1px, transparent 0)`,
          backgroundSize: "28px 28px"
        }}
      />

      {/* Ambient Soft Glows */}
      <div className="absolute -top-24 left-1/2 -translate-x-1/2 h-80 w-80 rounded-full bg-sky-200/30 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 left-1/2 -translate-x-1/2 h-80 w-80 rounded-full bg-indigo-100/40 blur-3xl pointer-events-none" />

      {/* Frameless Hero GIS Splash Layout */}
      <div className="relative z-10 w-full max-w-sm px-6 flex flex-col items-center text-center">
        
        {/* Animated Brand Emblem with Radar Rings */}
        <div className="relative flex items-center justify-center mb-6">
          <div className="absolute h-20 w-20 rounded-full bg-sky-500/10 animate-ping duration-1000" />
          <div className="absolute h-16 w-16 rounded-full bg-sky-500/15 animate-pulse" />
          <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-sky-600 to-blue-500 text-white shadow-xl shadow-sky-600/25">
            <Compass className="h-7 w-7 animate-[spin_12s_linear_infinite]" />
          </div>
        </div>

        {/* Brand Titles */}
        <div className="space-y-1.5 mb-7">
          <div className="flex items-center justify-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 font-sans">
              SHIFT
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-sky-100 text-sky-700 border border-sky-200">
              Desktop GIS v2.0
            </span>
          </div>
          <p className="text-xs font-medium text-slate-500 max-w-xs leading-relaxed">
            Geospatial Breakpoint & Automated Shoreline Change Analysis Workbench
          </p>
        </div>

        {/* Progress Bar Container */}
        <div className="w-full space-y-2.5 mb-7">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200/80 p-0.5">
            <div
              className="h-full rounded-full bg-gradient-to-r from-sky-500 via-blue-600 to-indigo-500 transition-all duration-300 ease-out shadow-sm"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Dynamic Status Text */}
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-600 px-0.5 min-h-[20px]">
            <span className="flex items-center gap-1.5 truncate">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-sky-500 animate-pulse" />
              <span className="truncate">{INIT_STEPS[stepIdx]}</span>
            </span>
            <span className="font-semibold text-sky-700 shrink-0 ml-2">{progress}%</span>
          </div>
        </div>

        {/* Feature Badges Strip */}
        <div className="w-full flex items-center justify-center gap-3.5 text-[11px] text-slate-400 font-medium">
          <span className="flex items-center gap-1">
            <Waves className="h-3.5 w-3.5 text-sky-500" /> USGS DSAS
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Layers className="h-3.5 w-3.5 text-blue-500" /> Breakpoints
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Globe className="h-3.5 w-3.5 text-indigo-500" /> WGS84 / UTM
          </span>
        </div>
      </div>
    </div>
  );
}
