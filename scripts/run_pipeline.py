import os
import json
import pandas as pd

from pipeline.raw_to_mp4 import raw_to_video
from pipeline.detect_impact import detect_impact
from pipeline.extract_clip import extract_clip
from pipeline.frame_mapping import load_frames, get_frame_at_timestamp


def process_take(take_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nProcessing: {take_dir}")

    # -------------------------
    # 1. RAW → MP4
    # -------------------------
    left_raw = os.path.join(take_dir, "left.raw8")
    right_raw = os.path.join(take_dir, "right.raw8")

    left_mp4 = os.path.join(take_dir, "left.mp4")
    right_mp4 = os.path.join(take_dir, "right.mp4")

    if not os.path.exists(left_mp4):
        raw_to_video(left_raw, left_mp4)

    if not os.path.exists(right_mp4):
        raw_to_video(right_raw, right_mp4)

    # -------------------------
    # 2. Detect impact
    # -------------------------
    impact_frame = detect_impact(left_mp4)

    # -------------------------
    # 3. Extract clips
    # -------------------------
    swing_dir = os.path.join(output_dir, os.path.basename(take_dir))
    os.makedirs(swing_dir, exist_ok=True)

    left_clip = os.path.join(swing_dir, "left.mp4")
    right_clip = os.path.join(swing_dir, "right.mp4")

    extract_clip(left_mp4, impact_frame, left_clip)
    extract_clip(right_mp4, impact_frame, right_clip)

    # -------------------------
    # 4. Load frame timestamps
    # -------------------------
    frames_csv = os.path.join(take_dir, "frames.csv")
    df = load_frames(frames_csv)

    impact_row = df.iloc[impact_frame]
    impact_ts = int(impact_row["timestamp_ns"])

    # -------------------------
    # 5. Build JSON
    # -------------------------
    data = {
        "take_id": os.path.basename(take_dir),
        "impact_frame": int(impact_frame),
        "impact_timestamp_ns": impact_ts,
        "videos": {
            "left": left_clip,
            "right": right_clip
        },
        "radar": None  # placeholder (next step)
    }

    with open(os.path.join(swing_dir, "data.json"), "w") as f:
        json.dump(data, f, indent=2)

    print(f"Done: {swing_dir}")


def run_all(input_root, output_root):
    takes = [
        os.path.join(input_root, d)
        for d in os.listdir(input_root)
        if d.startswith("swing_")
    ]

    for take in takes:
        process_take(take, output_root)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    run_all(args.input, args.output)
