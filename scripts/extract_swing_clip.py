#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from capture.swing_clip import extract_swing_clip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--take-dir", required=True, help="Recorded take folder to trim")
    parser.add_argument(
        "--impact-frame-index",
        required=True,
        type=int,
        help="Frame index of impact in the selected impact stream",
    )
    parser.add_argument(
        "--impact-stream",
        default="left",
        choices=["left", "right", "rgb"],
        help="Stream that owns the impact frame index",
    )
    parser.add_argument(
        "--padding-frames",
        type=int,
        default=20,
        help="Frames to keep before and after the impact frame",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional output directory for the extracted swing clip",
    )
    args = parser.parse_args()

    output_dir = extract_swing_clip(
        take_dir=Path(args.take_dir),
        impact_frame_index=args.impact_frame_index,
        padding_frames=args.padding_frames,
        impact_stream=args.impact_stream,
        output_dir=None if args.out is None else Path(args.out),
    )
    print(output_dir)


if __name__ == "__main__":
    main()
