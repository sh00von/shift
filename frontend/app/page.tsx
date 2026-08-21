"use client";

import { useEffect } from "react";
import { toast } from "sonner";
import { useStore } from "@/lib/store";
import { api } from "@/lib/api";
import { TopAppBar } from "@/components/shift/TopAppBar";
import { LayersTOC } from "@/components/shift/LayersTOC";
import { MapView } from "@/components/shift/MapView";
import { TransectInspector } from "@/components/shift/TransectInspector";
import { BottomInspector } from "@/components/shift/BottomInspector";
import { StatusBar } from "@/components/shift/StatusBar";
import { ProgressModal } from "@/components/shift/ProgressModal";
import { SplashScreen } from "@/components/shift/SplashScreen";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";

export default function Home() {
  const store = useStore();
  const {
    ready,
    sessionId,
    tocOpen,
    inspectorOpen,
    bottomDockOpen,
  } = store;

  useEffect(() => {
    store.init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onLoadDemo = async () => {
    if (!sessionId) return;
    store.setRunning(true, "Load Demo Dataset");
    try {
      const info = await api.loadDemo(sessionId);
      await store.reload();
      await Promise.all([store.refreshShorelines(), store.refreshBaseline()]);
      store.log(
        `Demo dataset loaded: ${info.shoreline.n_features} surveys (1990–2023) and synthetic offshore baseline.`,
        "SUCCESS"
      );
      store.setStatus("Demo dataset loaded. Ready for transect casting.", 0.3);
      toast.success("Loaded 6 shoreline surveys (1990–2023) & baseline.", {
        description: `${info.shoreline.n_features} shorelines, ${info.baseline.n_features} baseline features`,
      });
    } catch (e: any) {
      store.log(e.message || "Demo dataset load failed", "ERROR");
      toast.error(e.message || "Demo load failed");
    } finally {
      store.setRunning(false);
    }
  };

  const onClear = async () => {
    if (!sessionId) return;
    try {
      await api.clear(sessionId);
      await store.reload();
      useStore.setState({
        shorelines: null,
        baseline: null,
        transects: null,
        choropleth: null,
        forecast: null,
        selectedTransect: null,
      });
      store.log("Workspace session reset and layers cleared.", "INFO");
      store.setStatus("Session cleared. Ready for new input.", 0);
      toast.info("Workspace reset.");
    } catch (e: any) {
      toast.error("Failed to reset session.");
    }
  };

  if (!ready) {
    return <SplashScreen />;
  }

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-50 text-slate-900 font-sans">
      {/* Calm top app bar with contextual workflow actions */}
      <TopAppBar onLoadDemo={onLoadDemo} onClear={onClear} />

      {/* Main Desktop GIS Work Area */}
      <main className="flex min-h-0 flex-1 overflow-hidden">
        {/* NOTE: react-resizable-panels v4 treats bare numbers as pixels — sizes
            must be unit-less strings to be interpreted as percentages. */}
        {/* Groups are keyed on which panels are visible so react-resizable-panels
            cleanly remounts when a panel is toggled (v4 mishandles dynamic panels). */}
        <ResizablePanelGroup
          key={`h-${tocOpen}-${inspectorOpen}`}
          orientation="horizontal"
          className="min-h-0 flex-1"
        >
          {/* Left: Table of Contents (TOC) */}
          {tocOpen && (
            <>
              <ResizablePanel defaultSize="19" minSize="15" maxSize="28">
                <LayersTOC />
              </ResizablePanel>
              <ResizableHandle withHandle className="bg-slate-200 transition-colors hover:bg-primary" />
            </>
          )}

          {/* Center Column: Map Canvas + Collapsible Bottom Dock */}
          <ResizablePanel defaultSize={tocOpen && inspectorOpen ? "55" : "72"} minSize="35">
            <ResizablePanelGroup key={`v-${bottomDockOpen}`} orientation="vertical" className="min-h-0 flex-1">
              <ResizablePanel defaultSize={bottomDockOpen ? "60" : "100"} minSize="30">
                <MapView />
              </ResizablePanel>

              {bottomDockOpen && (
                <>
                  <ResizableHandle withHandle className="bg-slate-200 transition-colors hover:bg-primary" />
                  <ResizablePanel defaultSize="40" minSize="20" maxSize="70">
                    <BottomInspector />
                  </ResizablePanel>
                </>
              )}
            </ResizablePanelGroup>
          </ResizablePanel>

          {/* Right: Transect Inspector */}
          {inspectorOpen && (
            <>
              <ResizableHandle withHandle className="bg-slate-200 transition-colors hover:bg-primary" />
              <ResizablePanel defaultSize="26" minSize="20" maxSize="36">
                <TransectInspector />
              </ResizablePanel>
            </>
          )}
        </ResizablePanelGroup>
      </main>

      {/* Desktop GIS Status Bar */}
      <StatusBar />

      {/* Blocking progress modal for streamed jobs (analysis / cast / forecast) */}
      <ProgressModal />
    </div>
  );
}
