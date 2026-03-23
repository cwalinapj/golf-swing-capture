import queue
from dataclasses import asdict

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from .recorder import ImpactRecorder


def make_app(recorder: ImpactRecorder):
    app = FastAPI()

    @app.get("/", response_class=HTMLResponse)
    def index():
        return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Swing Capture</title>
  <style>
    body { font-family: sans-serif; margin: 24px; max-width: 900px; }
    button { font-size: 18px; padding: 12px 20px; margin-right: 10px; }
    pre { background: #111; color: #0f0; padding: 12px; border-radius: 8px; min-height: 200px; }
  </style>
</head>
<body>
  <h2>Swing Capture Control</h2>
  <p>
    <button onclick="startRec()">Start Recording</button>
    <button onclick="stopRec()">Stop Recording</button>
  </p>
  <pre id="status">loading...</pre>
  <script>
    async function startRec() {
      await fetch('/start', {method:'POST'});
      await refresh();
    }
    async function stopRec() {
      await fetch('/stop', {method:'POST'});
      await refresh();
    }
    async function refresh() {
      const r = await fetch('/status');
      const j = await r.json();
      document.getElementById('status').textContent = JSON.stringify(j, null, 2);
    }
    refresh();
    setInterval(refresh, 1000);
  </script>
</body>
</html>
        """

    @app.get("/status")
    def status():
        events = []
        try:
            while True:
                events.append(recorder.event_log.get_nowait())
        except queue.Empty:
            pass

        return {
            "recording": recorder.recording,
            "status": recorder.status_text,
            "current_take": None if recorder.current_take is None else asdict(recorder.current_take),
            "last_error": recorder.last_error,
            "new_events": events,
        }

    @app.post("/start")
    def start():
        ok, msg = recorder.start_recording()
        return JSONResponse({"ok": ok, "message": msg})

    @app.post("/stop")
    def stop():
        ok, msg = recorder.stop_recording()
        return JSONResponse({"ok": ok, "message": msg})

    return app
