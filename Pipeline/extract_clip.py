
def extract_all_swings(video_path, impact_frames, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    for i, frame_idx in enumerate(impact_frames):
        out_path = os.path.join(out_dir, f"swing_{i:03d}.mp4")
        extract_clip(video_path, frame_idx, out_path)
