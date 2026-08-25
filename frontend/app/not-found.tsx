"use client";

import Link from "next/link";
import { MapPin, ArrowLeft, Waves } from "lucide-react";

export default function NotFound() {
  return (
    <div className="relative flex h-full min-h-screen flex-col items-center justify-center overflow-hidden bg-[#0d1117]">
      {/* Animated wave lines */}
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full opacity-10"
        preserveAspectRatio="none"
      >
        {[0, 1, 2, 3, 4].map((i) => (
          <path
            key={i}
            d={`M0 ${300 + i * 60} Q300 ${260 + i * 60} 600 ${310 + i * 60} T1200 ${300 + i * 60} T1800 ${300 + i * 60}`}
            fill="none"
            stroke="#38bdf8"
            strokeWidth="1.5"
            style={{
              animation: `wave ${4 + i * 0.7}s ease-in-out infinite alternate`,
              animationDelay: `${i * 0.4}s`,
            }}
          />
        ))}
      </svg>

      {/* Radial glow */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-sky-500/5 blur-3xl" />

      <div className="relative z-10 flex flex-col items-center gap-6 text-center">
        {/* Icon */}
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-sky-500/20 bg-sky-500/10">
          <MapPin className="h-7 w-7 text-sky-400" />
        </div>

        {/* Code */}
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-[80px] font-bold leading-none tracking-tight text-white/10 select-none">
            404
          </span>
        </div>

        {/* Message */}
        <div className="space-y-2">
          <h1 className="text-xl font-semibold text-white">Page not found</h1>
          <p className="max-w-xs text-sm text-[#6b7280]">
            This shoreline doesn&apos;t exist in our dataset. The coordinate you&apos;re looking for has drifted offshore.
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2">
          <Link
            href="/"
            className="flex items-center gap-2 rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-medium text-sky-400 transition-colors hover:bg-sky-500/20 hover:text-sky-300"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to map
          </Link>
          <Link
            href="/docs"
            className="flex items-center gap-2 rounded-lg border border-[#252830] bg-[#1a1d23] px-4 py-2 text-sm font-medium text-[#888] transition-colors hover:border-[#333] hover:text-[#bbb]"
          >
            <Waves className="h-4 w-4" />
            Documentation
          </Link>
        </div>

        {/* Branding */}
        <p className="font-mono text-[10px] uppercase tracking-widest text-[#333]">
          SHIFT · Shoreline Intelligence
        </p>
      </div>

      <style>{`
        @keyframes wave {
          from { transform: translateX(0px); }
          to   { transform: translateX(-60px); }
        }
      `}</style>
    </div>
  );
}
