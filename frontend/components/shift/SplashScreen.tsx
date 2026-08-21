"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";

const INIT_STEPS = [
  "Initializing dynamics engine…",
  "Mounting spatial layers…",
  "Loading USGS DSAS statistics…",
  "Preparing changepoint regressors…",
  "Establishing runtime pipeline…",
];

export function SplashScreen() {
  const [stepIdx, setStepIdx] = useState(0);
  const [progress, setProgress] = useState(10);

  useEffect(() => {
    const stepInterval = setInterval(() => {
      setStepIdx((prev) => (prev + 1) % INIT_STEPS.length);
    }, 1200);

    const progressInterval = setInterval(() => {
      setProgress((prev) => (prev >= 95 ? 95 : prev + Math.floor(Math.random() * 8) + 4));
    }, 300);

    return () => {
      clearInterval(stepInterval);
      clearInterval(progressInterval);
    };
  }, []);

  return (
    <div className="relative flex h-screen w-screen flex-col items-center justify-center bg-white select-none">
      <div className="flex flex-col items-center max-w-xs w-full px-4">
        {/* Logo */}
        <Image
          src="/logo.png"
          alt="SHIFT Logo"
          width={72}
          height={72}
          className="rounded-2xl shadow-sm mb-5"
          priority
        />

        {/* Brand Name */}
        <h1 className="text-xl font-semibold tracking-[0.2em] text-slate-900 mb-1 font-sans">
          SHIFT
        </h1>
        <p className="text-[10px] tracking-widest text-slate-400 uppercase mb-7 text-center">
          Shoreline & River Bank Dynamics
        </p>

        {/* Minimal Thin Progress Bar */}
        <div className="h-[2px] w-40 bg-slate-200/80 overflow-hidden relative rounded-full">
          <div
            className="h-full bg-slate-900 transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Percentage Counter */}
        <div className="text-[10px] tracking-[0.2em] font-mono text-slate-400 mt-3 font-medium">
          {progress.toString().padStart(2, "0")}%
        </div>

        {/* Dynamic Minimal Sub-label */}
        <p className="text-[9px] tracking-widest text-slate-400 uppercase mt-6 text-center truncate max-w-full px-2">
          {INIT_STEPS[stepIdx]}
        </p>
      </div>
    </div>
  );
}
