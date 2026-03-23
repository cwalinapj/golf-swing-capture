"""Flask web interface for the golf swing capture application."""

import time

from flask import Flask, Response, jsonify, render_template_string

from capture.config import Config
from capture.recorder import GolfSwingRecorder

# ---------------------------------------------------------------------------
# HTML template (inline so no separate templates/ directory is required)
# ---------------------------------------------------------------------------
_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Golf Swing Capture</title>
  <style>
    body { font-family: sans-serif; background: #1a1a2e; color: #eee;
           display: flex; flex-direction: column; align-items: center;
           padding: 2rem; margin: 0; }
    h1   { color: #e94560; margin-bottom: 1rem; }
    img  { border: 3px solid #e94560; border-radius: 8px; max-width: 100%; }
    .controls { display: flex; gap: 1rem; margin-top: 1.5rem; }
    button { padding: .6rem 1.8rem; border: none; border-radius: 6px;
             font-size: 1rem; cursor: pointer; transition: opacity .2s; }
    button:hover { opacity: .85; }
    #btnStart { background: #4caf50; color: #fff; }
    #btnStop  { background: #e94560; color: #fff; }
    #status   { margin-top: 1rem; font-size: .95rem; min-height: 1.4em; }
  </style>
</head>
<body>
  <h1>⛳ Golf Swing Capture</h1>
  <img id="feed" src="/video_feed" alt="Live camera feed" />
  <div class="controls">
    <button id="btnStart" onclick="startRec()">▶ Start Recording</button>
    <button id="btnStop"  onclick="stopRec()">■ Stop Recording</button>
  </div>
  <p id="status"></p>
  <script>
    async function startRec() {
      const r = await fetch('/start', { method: 'POST' });
      const d = await r.json();
      document.getElementById('status').textContent =
        d.error ? 'Error: ' + d.error : 'Recording → ' + d.file;
    }
    async function stopRec() {
      const r = await fetch('/stop', { method: 'POST' });
      const d = await r.json();
      document.getElementById('status').textContent =
        d.error ? 'Error: ' + d.error : 'Saved: ' + d.file;
    }
  </script>
</body>
</html>
"""


def _mjpeg_stream(recorder: GolfSwingRecorder):
    """Generator that yields MJPEG frames from the recorder."""
    while True:
        frame = recorder.get_frame()
        if frame is None:
            time.sleep(1.0 / (recorder._config.FPS or 30))
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )


def create_app(config: Config | None = None) -> Flask:
    """Create and configure the Flask application."""
    cfg = config or Config()
    recorder = GolfSwingRecorder(cfg)
    recorder.open()

    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template_string(_INDEX_HTML)

    @app.route("/video_feed")
    def video_feed():
        return Response(
            _mjpeg_stream(recorder),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.route("/start", methods=["POST"])
    def start_recording():
        filepath = recorder.start_recording()
        if filepath is None:
            return jsonify({"error": "Camera not available or already recording"}), 400
        return jsonify({"status": "recording", "file": filepath})

    @app.route("/stop", methods=["POST"])
    def stop_recording():
        filepath = recorder.stop_recording()
        if filepath is None:
            return jsonify({"error": "Not currently recording"}), 400
        return jsonify({"status": "stopped", "file": filepath})

    @app.route("/status")
    def recording_status():
        return jsonify(
            {
                "is_recording": recorder.is_recording,
                "current_file": recorder.current_file,
            }
        )

    @app.teardown_appcontext
    def shutdown(_exc):
        recorder.close()

    return app
