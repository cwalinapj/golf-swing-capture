
import os

from pipeline.raw_to_mp4 import raw_to_video
from pipeline.detect_impacts_multi import detect_impacts
from pipeline.extract_clip import extract_clip
from pipeline.frame_mapping import load_frames
from pipeline.sync_radar import load_radar, match_radar

def run_session(session_dir, output_dir, radar_csv):
    os.makedirs(output_dir, exist_ok=True)

    left_raw = os.path.join(session_dir, "left.raw8")
    right_raw = os.path.join(session_dir, "right.raw8")

    left_mp4 = os.path.join(session_dir, "left.mp4")
    right_mp4 = os.path.join(session_dir, "right.mp4")

    raw_to_video(left_raw, left_mp4)
    raw_to_video(right_raw, right_mp4)

    impacts = detect_impacts(left_mp4)

    frames_df = load_frames(os.path.join(session_dir, "frames.csv"))
    radar_df = load_radar(radar_csv)

    for i, frame_idx in enumerate(impacts):
        swing_dir = os.path.join(output_dir, f"swing_{i:03d}")
        os.makedirs(swing_dir, exist_ok=True)

        # Extract clips
        extract_clip(left_mp4, frame_idx, os.path.join(swing_dir, "left.mp4"))
        extract_clip(right_mp4, frame_idx, os.path.join(swing_dir, "right.mp4"))

        # Timestamp
        ts = int(frames_df.iloc[frame_idx]["timestamp_ns"])

        radar = match_radar(radar_df, ts)

        # JSON
        data = {
            "swing_id": i,
            "impact_frame": int(frame_idx),
            "timestamp_ns": ts,
            "radar": radar
        }

        with open(os.path.join(swing_dir, "data.json"), "w") as f:
            json.dump(data, f, indent=2)

    print(f"Session complete: {len(impacts)} swings")
