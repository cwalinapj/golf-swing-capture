#!/usr/bin/env python3
"""Convert recorded raw frame streams into video files."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import cv2
import numpy as np


@dataclass(frozen=True)
class StreamSpec:
    name: str
    raw_name: str
    video_name: str
    width: int
    height: int
    fps: int
    channels: int
    csv_name: str

    @property
    def frame_bytes(self) -> int:
        return self.width * self.height * self.channels


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("take_dir", help="Path to a captured take directory")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory for generated videos and metadata (default: take directory)",
    )
    parser.add_argument(
        "--streams",
        nargs="+",
        choices=("left", "right", "rgb"),
        default=("left", "right", "rgb"),
        help="Streams to convert",
    )
    parser.add_argument(
        "--codec",
        default="mp4v",
        help="FourCC codec for OpenCV video writer (default: mp4v)",
    )
    parser.add_argument(
        "--metadata-name",
        default="video_assets.json",
        help="Generated metadata filename (default: video_assets.json)",
    )
    return parser.parse_args()


def load_manifest(take_dir: Path) -> dict:
    manifest_path = take_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {take_dir}")
    return json.loads(manifest_path.read_text())


def build_specs(manifest: dict) -> Dict[str, StreamSpec]:
    specs = {
        "left": StreamSpec(
            name="left",
            raw_name="left.raw8",
            video_name="left.mp4",
            width=int(manifest["mono_width"]),
            height=int(manifest["mono_height"]),
            fps=int(manifest["mono_fps"]),
            channels=1,
            csv_name="left",
        ),
        "right": StreamSpec(
            name="right",
            raw_name="right.raw8",
            video_name="right.mp4",
            width=int(manifest["mono_width"]),
            height=int(manifest["mono_height"]),
            fps=int(manifest["mono_fps"]),
            channels=1,
            csv_name="right",
        ),
    }
    if manifest.get("rgb_enabled"):
        specs["rgb"] = StreamSpec(
            name="rgb",
            raw_name="rgb.rawbgr",
            video_name="rgb.mp4",
            width=int(manifest["rgb_width"]),
            height=int(manifest["rgb_height"]),
            fps=int(manifest["rgb_fps"]),
            channels=3,
            csv_name="rgb",
        )
    return specs


def read_frame_rows(frames_csv: Path) -> Dict[str, List[dict]]:
    rows: Dict[str, List[dict]] = {"left": [], "right": [], "rgb": []}
    if not frames_csv.exists():
        return rows

    with frames_csv.open(newline="") as handle:
        for row in csv.DictReader(handle):
            rows.setdefault(row["stream"], []).append(row)
    return rows


def iter_raw_frames(raw_path: Path, spec: StreamSpec) -> Iterable[np.ndarray]:
    with raw_path.open("rb") as handle:
        while True:
            payload = handle.read(spec.frame_bytes)
            if not payload:
                break
            if len(payload) != spec.frame_bytes:
                raise ValueError(
                    f"{raw_path} ends with a partial {spec.name} frame: "
                    f"expected {spec.frame_bytes} bytes, got {len(payload)}"
                )

            frame = np.frombuffer(payload, dtype=np.uint8)
            if spec.channels == 1:
                yield frame.reshape(spec.height, spec.width)
            else:
                yield frame.reshape(spec.height, spec.width, spec.channels)


def open_writer(video_path: Path, spec: StreamSpec, codec: str) -> cv2.VideoWriter:
    fourcc = cv2.VideoWriter_fourcc(*codec)
    is_color = spec.channels == 3
    writer = cv2.VideoWriter(
        str(video_path),
        fourcc,
        spec.fps,
        (spec.width, spec.height),
        isColor=is_color,
    )
    if not writer.isOpened():
        raise RuntimeError(f"failed to open video writer for {video_path}")
    return writer


def convert_stream(
    raw_path: Path,
    video_path: Path,
    spec: StreamSpec,
    frame_rows: List[dict],
    codec: str,
) -> dict:
    writer = open_writer(video_path, spec, codec)
    frame_count = 0
    try:
        for frame in iter_raw_frames(raw_path, spec):
            writer.write(frame)
            frame_count += 1
    finally:
        writer.release()

    timestamps = [float(row["timestamp_sec"]) for row in frame_rows[:frame_count]]
    if frame_rows and len(frame_rows) != frame_count:
        print(
            f"warning: {spec.name} has {frame_count} raw frames but "
            f"{len(frame_rows)} rows in frames.csv",
            flush=True,
        )

    return {
        "stream": spec.name,
        "raw_path": str(raw_path),
        "video_path": str(video_path),
        "frame_count": frame_count,
        "fps": spec.fps,
        "width": spec.width,
        "height": spec.height,
        "channels": spec.channels,
        "timestamp_start_sec": timestamps[0] if timestamps else None,
        "timestamp_end_sec": timestamps[-1] if timestamps else None,
    }


def main() -> None:
    args = parse_args()
    take_dir = Path(args.take_dir).expanduser().resolve()
    out_dir = Path(args.out_dir or take_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(take_dir)
    specs = build_specs(manifest)
    frame_rows = read_frame_rows(take_dir / "frames.csv")

    outputs = []
    for stream_name in args.streams:
        spec = specs.get(stream_name)
        if spec is None:
            print(f"skipping unavailable stream: {stream_name}", flush=True)
            continue

        raw_path = take_dir / spec.raw_name
        if not raw_path.exists():
            print(f"skipping missing raw stream: {raw_path}", flush=True)
            continue

        video_path = out_dir / spec.video_name
        stream_info = convert_stream(raw_path, video_path, spec, frame_rows.get(stream_name, []), args.codec)
        outputs.append(stream_info)
        print(f"wrote {stream_name} video: {video_path}", flush=True)

    payload = {
        "take_dir": str(take_dir),
        "output_dir": str(out_dir),
        "codec": args.codec,
        "videos": outputs,
    }
    metadata_path = out_dir / args.metadata_name
    metadata_path.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2), flush=True)


if __name__ == "__main__":
    main()

