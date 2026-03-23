#!/usr/bin/env python3
"""Assemble take metadata, generated videos, and impact detection into one JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("take_dir", help="Path to a captured take directory")
    parser.add_argument(
        "--video-assets",
        default=None,
        help="Path to video_assets.json (default: take_dir/video_assets.json)",
    )
    parser.add_argument(
        "--impact",
        default=None,
        help="Path to impact.json (default: take_dir/impact.json)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON path (default: take_dir/swing.json)",
    )
    return parser.parse_args()


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def infer_video_assets(take_dir: Path) -> Dict[str, Any]:
    files = {
        "left": take_dir / "left.mp4",
        "right": take_dir / "right.mp4",
        "rgb": take_dir / "rgb.mp4",
    }
    videos = [
        {
            "stream": stream,
            "video_path": str(path),
        }
        for stream, path in files.items()
        if path.exists()
    ]
    return {
        "take_dir": str(take_dir),
        "output_dir": str(take_dir),
        "videos": videos,
    }


def main() -> None:
    args = parse_args()
    take_dir = Path(args.take_dir).expanduser().resolve()

    manifest_path = take_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {take_dir}")
    manifest = json.loads(manifest_path.read_text())

    video_assets_path = Path(args.video_assets or take_dir / "video_assets.json").expanduser().resolve()
    impact_path = Path(args.impact or take_dir / "impact.json").expanduser().resolve()

    video_assets = read_json(video_assets_path) or infer_video_assets(take_dir)
    impact = read_json(impact_path)

    output = {
        "take": manifest,
        "assets": video_assets,
        "impact_detection": impact,
    }

    out_path = Path(args.out or take_dir / "swing.json").expanduser().resolve()
    out_path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2), flush=True)


if __name__ == "__main__":
    main()
