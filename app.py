import argparse
import signal
import sys
import threading
from pathlib import Path

import uvicorn

from capture.recorder import ImpactRecorder
from capture.web import make_app


def cli_loop(recorder: ImpactRecorder):
    print("\nCLI controls:")
    print("  r = start recording")
    print("  s = stop recording")
    print("  q = quit\n")

    while True:
        cmd = input("> ").strip().lower()
        if cmd == "r":
            ok, msg = recorder.start_recording()
            print(msg)
        elif cmd == "s":
            ok, msg = recorder.stop_recording()
            print(msg)
        elif cmd == "q":
            break
        else:
            print("commands: r / s / q")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Base output folder")
    parser.add_argument("--device-id", default=None)
    parser.add_argument("--no-rgb", action="store_true")
    parser.add_argument("--mono-exposure-us", type=int, default=120)
    parser.add_argument("--mono-iso", type=int, default=400)
    parser.add_argument("--rgb-exposure-us", type=int, default=120)
    parser.add_argument("--rgb-iso", type=int, default=200)
    parser.add_argument("--rgb-focus", type=int, default=120)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    recorder = ImpactRecorder(
        base_dir=out_dir,
        mono_exposure_us=args.mono_exposure_us,
        mono_iso=args.mono_iso,
        rgb_enabled=not args.no_rgb,
        rgb_exposure_us=args.rgb_exposure_us,
        rgb_iso=args.rgb_iso,
        rgb_focus=args.rgb_focus,
        device_id=args.device_id,
    )

    def shutdown_handler(sig, frame):
        recorder.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    recorder.start()

    app = make_app(recorder)
    server = uvicorn.Server(
        uvicorn.Config(app, host=args.host, port=args.port, log_level="info")
    )

    t = threading.Thread(target=server.run, daemon=True)
    t.start()

    try:
        cli_loop(recorder)
    finally:
        recorder.stop()


if __name__ == "__main__":
    main()
