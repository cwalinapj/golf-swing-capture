# golf-swing-capture

Local capture tool for an OAK-D Lite golf impact rig.

Features:
- CLI controls:
  - `r` = start recording
  - `s` = stop recording
  - `q` = quit
- Web UI:
  - Start button
  - Stop button
  - live status page
- Timestamped take folders
- Per-frame timestamps
- Raw capture:
  - left mono
  - right mono
  - optional RGB

## Output format

Each take is saved like:

```text
golf_takes/
  swing_YYYYMMDD_HHMMSS_mmm/
    manifest.json
    frames.csv
    left.raw8
    right.raw8
    rgb.rawbgr

SETUP

python3 -m venv oak-env
source oak-env/bin/activate
pip install -r requirements.txt

Run

python app.py \
  --out /Volumes/Torrents/golf_takes \
  --mono-exposure-us 120 \
  --mono-iso 400 \
  --rgb-exposure-us 120 \
  --rgb-iso 200 \
  --rgb-focus 120

Then open:

http://127.0.0.1:8000

   CLI controls
	•	r = start recording
	•	s = stop recording
	•	q = quit

Notes
	•	left.raw8 and right.raw8 are concatenated 8-bit grayscale frames
	•	rgb.rawbgr is concatenated BGR frames
	•	frames.csv contains per-frame timestamps and sequence numbers
	•	manifest.json stores take-level metadata

---

## Pipeline

Post-process a recorded take with:

```bash
python pipeline/split_raw_to_video.py /path/to/swing_YYYYMMDD_HHMMSS_mmm
python pipeline/detect_impact.py /path/to/swing_YYYYMMDD_HHMMSS_mmm
python pipeline/build_swing_json.py /path/to/swing_YYYYMMDD_HHMMSS_mmm
```

This produces:

- `left.mp4`, `right.mp4`, and `rgb.mp4` when those streams exist
- `video_assets.json` describing generated videos
- `impact.json` with the strongest mono-frame change candidate
- `swing.json` combining the take manifest, generated assets, and impact result

---

## `requirements.txt`

```txt
depthai
fastapi
uvicorn
