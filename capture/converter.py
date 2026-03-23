import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import cv2
import numpy as np

from .config import MONO_FPS, MONO_H, MONO_W


STREAM_SPECS = {
    "left": {
        "raw_name": "left.raw8",
        "video_name": "left.mp4",
        "width_key": "mono_width",
        "height_key": "mono_height",
        "fps_key": "mono_fps",
    },
    "right": {
        "raw_name": "right.raw8",
        "video_name": "right.mp4",
        "width_key": "mono_width",
        "height_key": "mono_height",
        "fps_key": "mono_fps",
    },
}


@dataclass
class ConversionResult:
    stream: str
    output_path: Path
    frames_written: int
    fps: float
    width: int
    height: int
    truncated: bool


def load_manifest(take_dir: Path) -> dict:
    manifest_path = take_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text())


def load_stream_timestamps(frames_path: Path, stream_name: str) -> list[float]:
    timestamps = []
    with frames_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("stream") != stream_name:
                continue
            timestamps.append(float(row["timestamp_sec"]))
    return timestamps


def infer_fps(timestamps: list[float], fallback_fps: float) -> float:
    if len(timestamps) < 2:
        return fallback_fps

    deltas = [
        later - earlier
        for earlier, later in zip(timestamps, timestamps[1:])
        if later > earlier
    ]
    if not deltas:
        return fallback_fps

    median_delta = median(deltas)
    if median_delta <= 0:
        return fallback_fps

    inferred = 1.0 / median_delta
    return inferred if inferred > 0 else fallback_fps


def convert_stream(take_dir: Path, stream_name: str, overwrite: bool = False) -> ConversionResult:
    if stream_name not in STREAM_SPECS:
        raise ValueError(f"Unsupported stream: {stream_name}")

    frames_path = take_dir / "frames.csv"
    if not frames_path.exists():
        raise FileNotFoundError(f"Missing frames.csv in {take_dir}")

    spec = STREAM_SPECS[stream_name]
    manifest = load_manifest(take_dir)
    width = int(manifest.get(spec["width_key"], MONO_W))
    height = int(manifest.get(spec["height_key"], MONO_H))
    fallback_fps = float(manifest.get(spec["fps_key"], MONO_FPS))

    raw_path = take_dir / spec["raw_name"]
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing {spec['raw_name']} in {take_dir}")

    output_path = take_dir / spec["video_name"]
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"{output_path} already exists; pass --overwrite to replace it")

    timestamps = load_stream_timestamps(frames_path, stream_name)
    if not timestamps:
        raise ValueError(f"No {stream_name} rows found in {frames_path}")

    frame_size = width * height
    raw_size = raw_path.stat().st_size
    if raw_size % frame_size != 0:
        raise ValueError(
            f"{raw_path.name} size ({raw_size}) is not divisible by frame size ({frame_size})"
        )

    raw_frame_count = raw_size // frame_size
    csv_frame_count = len(timestamps)
    frame_count = min(raw_frame_count, csv_frame_count)
    if frame_count == 0:
        raise ValueError(f"No frames available for {stream_name}")

    fps = infer_fps(timestamps[:frame_count], fallback_fps)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
        True,
    )
    if not writer.isOpened():
        raise RuntimeError(f"Unable to open video writer for {output_path}")

    truncated = raw_frame_count != csv_frame_count

    try:
        with raw_path.open("rb") as handle:
            for _ in range(frame_count):
                frame_bytes = handle.read(frame_size)
                if len(frame_bytes) != frame_size:
                    raise ValueError(f"Unexpected end of file while reading {raw_path.name}")

                frame = np.frombuffer(frame_bytes, dtype=np.uint8).reshape((height, width))
                writer.write(cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR))
    finally:
        writer.release()

    return ConversionResult(
        stream=stream_name,
        output_path=output_path,
        frames_written=frame_count,
        fps=fps,
        width=width,
        height=height,
        truncated=truncated,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a raw mono take into MP4 video files")
    parser.add_argument("take_dir", help="Take folder containing frames.csv and *.raw8 files")
    parser.add_argument(
        "--streams",
        nargs="+",
        choices=sorted(STREAM_SPECS),
        default=sorted(STREAM_SPECS),
        help="Streams to convert",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing mp4 files if they already exist",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    take_dir = Path(args.take_dir).expanduser().resolve()
    if not take_dir.is_dir():
        raise NotADirectoryError(f"Take directory not found: {take_dir}")

    for stream_name in args.streams:
        result = convert_stream(take_dir, stream_name, overwrite=args.overwrite)
        note = " (frame count limited by shorter of raw file and frames.csv)" if result.truncated else ""
        print(
            f"{result.stream}: wrote {result.frames_written} frames to {result.output_path} "
            f"at {result.fps:.2f} fps ({result.width}x{result.height}){note}"
        )


if __name__ == "__main__":
    main()
