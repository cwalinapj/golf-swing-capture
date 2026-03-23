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
