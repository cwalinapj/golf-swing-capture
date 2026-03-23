import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


STREAM_FILE_NAMES = {
    "left": "left.raw8",
    "right": "right.raw8",
    "rgb": "rgb.rawbgr",
}


@dataclass(frozen=True)
class FrameRow:
    stream: str
    frame_idx: int
    timestamp_sec: float
    sequence_num: int
    byte_count: int


def _read_manifest(take_dir: Path) -> dict:
    manifest_path = take_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    return json.loads(manifest_path.read_text())


def _read_frame_rows(take_dir: Path) -> dict[str, list[FrameRow]]:
    frames_path = take_dir / "frames.csv"
    if not frames_path.exists():
        raise FileNotFoundError(f"Missing frames.csv: {frames_path}")

    rows_by_stream: dict[str, list[FrameRow]] = {}
    with frames_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            frame = FrameRow(
                stream=row["stream"],
                frame_idx=int(row["frame_idx"]),
                timestamp_sec=float(row["timestamp_sec"]),
                sequence_num=int(row["sequence_num"]),
                byte_count=int(row["bytes"]),
            )
            rows_by_stream.setdefault(frame.stream, []).append(frame)

    for rows in rows_by_stream.values():
        rows.sort(key=lambda frame: frame.frame_idx)

    return rows_by_stream


def _frame_size_bytes(manifest: dict, stream_name: str) -> int:
    if stream_name in {"left", "right"}:
        return int(manifest["mono_width"]) * int(manifest["mono_height"])
    if stream_name == "rgb":
        return int(manifest["rgb_width"]) * int(manifest["rgb_height"]) * 3
    raise ValueError(f"Unsupported stream: {stream_name}")


def _slice_raw_frames(
    source_path: Path,
    dest_path: Path,
    frame_size_bytes: int,
    start_frame_idx: int,
    end_frame_idx: int,
):
    frame_count = end_frame_idx - start_frame_idx + 1
    if frame_count <= 0:
        raise ValueError("Frame range must not be empty")

    byte_offset = start_frame_idx * frame_size_bytes
    expected_size = frame_count * frame_size_bytes

    with source_path.open("rb") as src, dest_path.open("wb") as dst:
        src.seek(byte_offset)
        chunk = src.read(expected_size)
        if len(chunk) != expected_size:
            raise ValueError(
                f"Unexpected raw frame size for {source_path.name}: "
                f"expected {expected_size} bytes, got {len(chunk)}"
            )
        dst.write(chunk)


def extract_swing_clip(
    take_dir: Path,
    impact_frame_index: int,
    padding_frames: int = 20,
    impact_stream: str = "left",
    output_dir: Optional[Path] = None,
) -> Path:
    if padding_frames < 0:
        raise ValueError("padding_frames must be non-negative")

    take_dir = take_dir.expanduser().resolve()
    manifest = _read_manifest(take_dir)
    rows_by_stream = _read_frame_rows(take_dir)

    impact_rows = rows_by_stream.get(impact_stream)
    if not impact_rows:
        raise ValueError(f"No frames found for impact stream: {impact_stream}")

    impact_position = None
    for position, row in enumerate(impact_rows):
        if row.frame_idx == impact_frame_index:
            impact_position = position
            break
    if impact_position is None:
        raise ValueError(
            f"Impact frame index {impact_frame_index} not found in {impact_stream} stream"
        )

    start_position = max(0, impact_position - padding_frames)
    end_position = min(len(impact_rows) - 1, impact_position + padding_frames)
    impact_timestamp = impact_rows[impact_position].timestamp_sec
    clip_start_ts = impact_rows[start_position].timestamp_sec
    clip_end_ts = impact_rows[end_position].timestamp_sec

    if output_dir is None:
        output_dir = (
            take_dir.parent
            / f"{take_dir.name}_clip_{impact_stream}_{impact_frame_index:06d}"
        )
    output_dir = output_dir.expanduser().resolve()

    selected_rows: list[FrameRow] = []
    selected_stream_rows: dict[str, list[FrameRow]] = {}
    clip_streams: dict[str, dict[str, float | int | str]] = {}

    for stream_name, stream_rows in rows_by_stream.items():
        clip_rows = [
            row
            for row in stream_rows
            if clip_start_ts <= row.timestamp_sec <= clip_end_ts
        ]
        if not clip_rows:
            continue

        selected_rows.extend(clip_rows)
        selected_stream_rows[stream_name] = clip_rows

        start_frame_idx = clip_rows[0].frame_idx
        end_frame_idx = clip_rows[-1].frame_idx
        clip_streams[stream_name] = {
            "source_file": STREAM_FILE_NAMES[stream_name],
            "start_frame_idx": start_frame_idx,
            "end_frame_idx": end_frame_idx,
            "frame_count": len(clip_rows),
            "start_timestamp_sec": clip_rows[0].timestamp_sec,
            "end_timestamp_sec": clip_rows[-1].timestamp_sec,
        }

    if not clip_streams:
        raise ValueError("No frames fell within the selected clip window")

    output_dir.mkdir(parents=True, exist_ok=False)

    for stream_name, clip_rows in selected_stream_rows.items():
        source_file_name = STREAM_FILE_NAMES[stream_name]
        source_path = take_dir / source_file_name
        if not source_path.exists():
            raise FileNotFoundError(f"Missing raw stream file: {source_path}")
        _slice_raw_frames(
            source_path=source_path,
            dest_path=output_dir / source_file_name,
            frame_size_bytes=_frame_size_bytes(manifest, stream_name),
            start_frame_idx=clip_rows[0].frame_idx,
            end_frame_idx=clip_rows[-1].frame_idx,
        )

    selected_rows.sort(key=lambda row: (row.timestamp_sec, row.stream, row.frame_idx))

    with (output_dir / "frames.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["stream", "frame_idx", "timestamp_sec", "sequence_num", "bytes"])
        for row in selected_rows:
            writer.writerow(
                [
                    row.stream,
                    row.frame_idx,
                    row.timestamp_sec,
                    row.sequence_num,
                    row.byte_count,
                ]
            )

    clip_manifest = dict(manifest)
    clip_manifest.update(
        {
            "take_id": output_dir.name,
            "output_dir": str(output_dir),
            "source_take_id": manifest.get("take_id"),
            "source_output_dir": str(take_dir),
            "clip_type": "swing_window",
            "impact_stream": impact_stream,
            "impact_frame_index": impact_frame_index,
            "impact_timestamp_sec": impact_timestamp,
            "padding_frames": padding_frames,
            "clip_start_timestamp_sec": clip_start_ts,
            "clip_end_timestamp_sec": clip_end_ts,
            "clip_streams": clip_streams,
        }
    )
    (output_dir / "manifest.json").write_text(json.dumps(clip_manifest, indent=2))

    return output_dir
