import os
import json

def build_dataset(swings, timestamps, radar_df, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    dataset = []

    for i, (frame_idx, ts) in enumerate(zip(swings, timestamps)):
        radar = match_radar(radar_df, ts)

        entry = {
            "swing_id": i,
            "impact_frame": int(frame_idx),
            "timestamp_ns": int(ts),
            "radar": radar,
            "videos": {
                "left": f"swing_{i:03d}_left.mp4",
                "right": f"swing_{i:03d}_right.mp4"
            }
        }

        dataset.append(entry)

    with open(os.path.join(output_dir, "dataset.json"), "w") as f:
        json.dump(dataset, f, indent=2)
