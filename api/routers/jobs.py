"""WebSocket endpoints for long-running analysis jobs."""
from __future__ import annotations

import asyncio
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api import pipeline
from api.deps import log
from api.session import store

router = APIRouter()


async def _run_job(ws: WebSocket, s, fn):
    await ws.accept()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def progress(msg: str, prog: float):
        try:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "progress", "message": msg, "progress": prog})
        except Exception:
            pass

    async def worker():
        try:
            await asyncio.to_thread(fn, s, progress)
            await queue.put({"type": "done"})
        except asyncio.CancelledError:
            pass
        except Exception as ex:
            log(s, traceback.format_exc(), "ERROR")
            try:
                await queue.put({"type": "error", "message": str(ex)})
            except Exception:
                pass

    task = asyncio.create_task(worker())
    try:
        while True:
            frame = await queue.get()
            await ws.send_json(frame)
            if frame.get("type") in ("done", "error"):
                break
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as ex:
        log(s, f"WebSocket job error: {ex}", "ERROR")
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        try:
            await ws.close()
        except Exception:
            pass


@router.websocket("/session/{sid}/ws/preview")
async def ws_preview(ws: WebSocket, sid: str):
    s = store.get(sid)
    if s is None:
        await ws.close(code=4404)
        return
    await _run_job(ws, s, pipeline.preview_transects)


@router.websocket("/session/{sid}/ws/analyze")
async def ws_analyze(ws: WebSocket, sid: str):
    s = store.get(sid)
    if s is None:
        await ws.close(code=4404)
        return
    await _run_job(ws, s, pipeline.run_analysis)


@router.websocket("/session/{sid}/ws/aln2d")
async def ws_aln2d(ws: WebSocket, sid: str):
    s = store.get(sid)
    if s is None:
        await ws.close(code=4404)
        return
    await _run_job(ws, s, pipeline.run_aln2d)


@router.websocket("/session/{sid}/ws/forecast")
async def ws_forecast(ws: WebSocket, sid: str):
    s = store.get(sid)
    if s is None:
        await ws.close(code=4404)
        return
    await _run_job(ws, s, pipeline.generate_forecast)


@router.websocket("/session/{sid}/ws/montecarlo")
async def ws_montecarlo(ws: WebSocket, sid: str):
    s = store.get(sid)
    if s is None:
        await ws.close(code=4404)
        return
    await _run_job(ws, s, pipeline.run_montecarlo)


@router.websocket("/session/{sid}/ws/cbc")
async def ws_cbc(ws: WebSocket, sid: str):
    s = store.get(sid)
    if s is None:
        await ws.close(code=4404)
        return
    await _run_job(ws, s, pipeline.run_cbc)
