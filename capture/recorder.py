import csv
import json
import queue
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import depthai as dai

from .config import (
    MONO_W,
    MONO_H,
    MONO_FPS,
    RGB_W,
    RGB_H,
    RGB_FPS,
    now_local,
    ts_for_name,
    iso_ts,
)


def make_ctrl(exposure_us: int, iso: int, focus: Optional[int] = None):
    ctrl = dai.CameraControl()
    ctrl.setManualExposure(exposure_us, iso)
    ctrl.setAntiBandingMode(dai.CameraControl.AntiBandingMode.OFF)
    if focus is not None:
        ctrl.setManualFocus(focus)
    return ctrl


@dataclass
class TakeInfo:
    take_id: str
    started_at: str
    stopped_at: Optional[str]
    duration_sec: Optional[float]
    output_dir: str
    device_id: str
    mono_exposure_us: int
    mono_iso: int
    rgb_enabled: bool
    rgb_exposure_us: int
    rgb_iso: int
    rgb_focus: int
    mono_width: int
    mono_height: int
    mono_fps: int
    rgb_width: int
    rgb_height: int
    rgb_fps: int


class ImpactRecorder:
    def __init__(
        self,
        base_dir: Path,
        mono_exposure_us: int,
        mono_iso: int,
        rgb_enabled: bool,
        rgb_exposure_us: int,
        rgb_iso: int,
        rgb_focus: int,
        device_id: Optional[str] = None,
    ):
        self.base_dir = base_dir
        self.mono_exposure_us = mono_exposure_us
        self.mono_iso = mono_iso
        self.rgb_enabled = rgb_enabled
        self.rgb_exposure_us = rgb_exposure_us
        self.rgb_iso = rgb_iso
        self.rgb_focus = rgb_focus
        self.requested_device_id = device_id

        self.device_info = None
        self.device = None
        self.pipeline = None

        self.left_q = None
        self.right_q = None
        self.rgb_q = None

        self.left_ctrl_q = None
        self.right_ctrl_q = None
        self.rgb_ctrl_q = None

        self.running = False
        self.recording = False
        self.worker = None

        self.take_lock = threading.Lock()
        self.current_take: Optional[TakeInfo] = None

        self.left_file = None
        self.right_file = None
        self.rgb_file = None
        self.csv_file = None
        self.csv_writer = None

        self.left_idx = 0
        self.right_idx = 0
        self.rgb_idx = 0

        self.status_text = "idle"
        self.last_error = None
        self.event_log = queue.Queue()

    def log_event(self, msg: str):
        stamp = iso_ts(now_local())
        line = f"[{stamp}] {msg}"
        self.status_text = msg
        self.event_log.put(line)
        print(line, flush=True)

    def select_device(self):
        infos = dai.Device.getAllAvailableDevices()
        if not infos:
            raise RuntimeError("No OAK devices found")

        if self.requested_device_id:
            for info in infos:
                if info.getDeviceId() == self.requested_device_id:
                    return info
            raise RuntimeError(f"Requested device not found: {self.requested_device_id}")

        return infos[0]

    def setup(self):
        self.device_info = self.select_device()
        self.device = dai.Device(self.device_info)
        self.pipeline = dai.Pipeline(self.device)

        left = self.pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
        right = self.pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)

        self.left_q = left.requestOutput(
            (MONO_W, MONO_H), fps=MONO_FPS, type=dai.ImgFrame.Type.GRAY8
        ).createOutputQueue()

        self.right_q = right.requestOutput(
            (MONO_W, MONO_H), fps=MONO_FPS, type=dai.ImgFrame.Type.GRAY8
        ).createOutputQueue()

        self.left_ctrl_q = left.inputControl.createInputQueue()
        self.right_ctrl_q = right.inputControl.createInputQueue()

        if self.rgb_enabled:
            rgb = self.pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
            self.rgb_q = rgb.requestOutput(
                (RGB_W, RGB_H), fps=RGB_FPS, type=dai.ImgFrame.Type.BGR888p
            ).createOutputQueue()
            self.rgb_ctrl_q = rgb.inputControl.createInputQueue()

        self.pipeline.start()

        mono_ctrl = make_ctrl(self.mono_exposure_us, self.mono_iso)
        self.left_ctrl_q.send(mono_ctrl)
        self.right_ctrl_q.send(mono_ctrl)

        if self.rgb_enabled and self.rgb_ctrl_q is not None:
            rgb_ctrl = make_ctrl(self.rgb_exposure_us, self.rgb_iso, focus=self.rgb_focus)
            self.rgb_ctrl_q.send(rgb_ctrl)

        self.log_event(f"connected device {self.device_info.getDeviceId()}")

    def start(self):
        self.setup()
        self.running = True
        self.worker = threading.Thread(target=self.loop, daemon=True)
        self.worker.start()

    def stop(self):
        self.running = False
        if self.worker:
            self.worker.join(timeout=2.0)
        self.stop_recording()
        self.log_event("shutdown complete")

    def start_recording(self):
        with self.take_lock:
            if self.recording:
                return False, "already recording"

            dt = now_local()
            take_id = f"swing_{ts_for_name(dt)}"
            take_dir = self.base_dir / take_id
            take_dir.mkdir(parents=True, exist_ok=True)

            self.left_file = open(take_dir / "left.raw8", "ab")
            self.right_file = open(take_dir / "right.raw8", "ab")
            self.csv_file = open(take_dir / "frames.csv", "w", newline="")
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(["stream", "frame_idx", "timestamp_sec", "sequence_num", "bytes"])

            if self.rgb_enabled:
                self.rgb_file = open(take_dir / "rgb.rawbgr", "ab")

            self.left_idx = 0
            self.right_idx = 0
            self.rgb_idx = 0

            self.current_take = TakeInfo(
                take_id=take_id,
                started_at=iso_ts(dt),
                stopped_at=None,
                duration_sec=None,
                output_dir=str(take_dir),
                device_id=self.device_info.getDeviceId(),
                mono_exposure_us=self.mono_exposure_us,
                mono_iso=self.mono_iso,
                rgb_enabled=self.rgb_enabled,
                rgb_exposure_us=self.rgb_exposure_us,
                rgb_iso=self.rgb_iso,
                rgb_focus=self.rgb_focus,
                mono_width=MONO_W,
                mono_height=MONO_H,
                mono_fps=MONO_FPS,
                rgb_width=RGB_W,
                rgb_height=RGB_H,
                rgb_fps=RGB_FPS,
            )

            manifest_path = take_dir / "manifest.json"
            manifest_path.write_text(json.dumps(asdict(self.current_take), indent=2))

            self.recording = True
            self.log_event(f"recording started: {take_id}")
            return True, take_id

    def stop_recording(self):
        with self.take_lock:
            if not self.recording:
                return False, "not recording"

            stopped = now_local()
            started = datetime.fromisoformat(self.current_take.started_at)
            self.current_take.stopped_at = iso_ts(stopped)
            self.current_take.duration_sec = (stopped - started).total_seconds()

            take_dir = Path(self.current_take.output_dir)
            manifest_path = take_dir / "manifest.json"
            manifest_path.write_text(json.dumps(asdict(self.current_take), indent=2))

            if self.left_file:
                self.left_file.close()
                self.left_file = None
            if self.right_file:
                self.right_file.close()
                self.right_file = None
            if self.rgb_file:
                self.rgb_file.close()
                self.rgb_file = None
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None

            take_id = self.current_take.take_id
            self.current_take = None
            self.recording = False
            self.log_event(f"recording stopped: {take_id}")
            return True, take_id

    def write_frame_row(self, stream_name: str, frame_idx: int, pkt, arr_size: int):
        if self.csv_writer is None:
            return
        self.csv_writer.writerow([
            stream_name,
            frame_idx,
            pkt.getTimestamp().total_seconds(),
            pkt.getSequenceNum(),
            arr_size,
        ])

    def loop(self):
        try:
            while self.running:
                pkt_l = self.left_q.get()
                arr_l = pkt_l.getFrame()

                pkt_r = self.right_q.get()
                arr_r = pkt_r.getFrame()

                pkt_c = None
                arr_c = None
                if self.rgb_enabled and self.rgb_q is not None:
                    pkt_c = self.rgb_q.get()
                    arr_c = pkt_c.getCvFrame()

                if self.recording:
                    with self.take_lock:
                        if self.left_file:
                            arr_l.tofile(self.left_file)
                            self.write_frame_row("left", self.left_idx, pkt_l, arr_l.size)
                            self.left_idx += 1

                        if self.right_file:
                            arr_r.tofile(self.right_file)
                            self.write_frame_row("right", self.right_idx, pkt_r, arr_r.size)
                            self.right_idx += 1

                        if self.rgb_enabled and self.rgb_file and arr_c is not None and pkt_c is not None:
                            arr_c.tofile(self.rgb_file)
                            self.write_frame_row("rgb", self.rgb_idx, pkt_c, arr_c.size)
                            self.rgb_idx += 1

        except Exception as e:
            self.last_error = repr(e)
            self.log_event(f"error: {self.last_error}")
