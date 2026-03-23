#!/usr/bin/env python3
"""Detect the likely impact frame from recorded mono camera streams."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class MonoSpec:
    name: str
    raw_name: str
    width: int
    height: int

    @property
    def frame_bytes(self) -> int:
        return self.width * self.height


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("take_dir", help="Path to a captured take directory")
    parser.add_argument(
        "--streams",
        nargs="+",
        choices=("left", "right"),
        default=("left", "right"),
        help="Mono streams to analyze",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON path (default: take_dir/impact.json)",
    )
    parser.add_argument(
        "--min-frame-index",
        type=int,
        default=1,
        help="Ignore scores before this frame index (default: 1)",
    )
    return parser.parse_args()


def load_manifest(take_dir: Path) -> dict:
    manifest_path = take_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {take_dir}")
    return json.loads(manifest_path.read_text())


def read_frame_rows(frames_csv: Path) -> Dict[str, List[dict]]:
    rows: Dict[str, List[dict]] = {"left": [], "right": []}
    if not frames_csv.exists():
        return rows

    with frames_csv.open(newline="") as handle:
        for row in csv.DictReader(handle):
            rows.setdefault(row["stream"], []).append(row)
    return rows


def iter_mono_frames(raw_path: Path, spec: MonoSpec) -> Iterable[np.ndarray]:
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
            frame = np.frombuffer(payload, dtype=np.uint8).reshape(spec.height, spec.width)
            yield frame


def score_stream(raw_path: Path, spec: MonoSpec, min_frame_index: int) -> Tuple[Optional[dict], int]:
    best: Optional[dict] = None
    prev: Optional[np.ndarray] = None
    frame_count = 0

    for frame_count, frame in enumerate(iter_mono_frames(raw_path, spec), start=1):
        if prev is None:
            prev = frame
            continue

        diff = np.abs(frame.astype(np.int16) - prev.astype(np.int16))
        score = float(diff.mean())
        peak_delta = int(diff.max())
        candidate = {
            "frame_idx": frame_count - 1,
            "score": score,
            "peak_delta": peak_delta,
        }
        if candidate["frame_idx"] >= min_frame_index and (
            best is None or candidate["score"] > best["score"]
        ):
            best = candidate
        prev = frame

    return best, frame_count


def build_specs(manifest: dict) -> Dict[str, MonoSpec]:
    return {
        "left": MonoSpec(
            name="left",
            raw_name="left.raw8",
            width=int(manifest["mono_width"]),
            height=int(manifest["mono_height"]),
        ),
        "right": MonoSpec(
            name="right",
            raw_name="right.raw8",
            width=int(manifest["mono_width"]),
            height=int(manifest["mono_height"]),
        ),
    }


def add_timestamp(candidate: Optional[dict], rows: List[dict]) -> Optional[dict]:
    if candidate is None:
        return None

    result = dict(candidate)
    frame_idx = result["frame_idx"]
    timestamp = None
    if 0 <= frame_idx < len(rows):
        timestamp = float(rows[frame_idx]["timestamp_sec"])
    result["timestamp_sec"] = timestamp
    return result


def main() -> None:
    args = parse_args()
    take_dir = Path(args.take_dir).expanduser().resolve()
    manifest = load_manifest(take_dir)
    specs = build_specs(manifest)
    frame_rows = read_frame_rows(take_dir / "frames.csv")

    per_stream = []
    best_overall = None
    for stream_name in args.streams:
        spec = specs[stream_name]
        raw_path = take_dir / spec.raw_name
        if not raw_path.exists():
            print(f"skipping missing raw stream: {raw_path}", flush=True)
            continue

        best, frame_count = score_stream(raw_path, spec, args.min_frame_index)
        best = add_timestamp(best, frame_rows.get(stream_name, []))
        entry = {
            "stream": stream_name,
            "raw_path": str(raw_path),
            "frame_count": frame_count,
            "best_candidate": best,
        }
        per_stream.append(entry)

        if best is not None and (best_overall is None or best["score"] > best_overall["score"]):
            best_overall = {"stream": stream_name, **best}

    payload = {
        "take_dir": str(take_dir),
        "min_frame_index": args.min_frame_index,
        "impact": best_overall,
        "streams": per_stream,
    }

    out_path = Path(args.out or take_dir / "impact.json").expanduser().resolve()
    out_path.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2), flush=True)


if __name__ == "__main__":
    main()

