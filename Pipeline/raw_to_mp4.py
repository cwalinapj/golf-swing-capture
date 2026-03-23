import os
import cv2
import numpy as np
import csv

WIDTH = 640
HEIGHT = 400
FPS = 175  # match your capture

def raw_to_video(raw_path, out_path):
    frame_size = WIDTH * HEIGHT  # bytes per frame

    with open(raw_path, "rb") as f:
        raw_data = f.read()

    num_frames = len(raw_data) // frame_size
    print(f"Frames detected: {num_frames}")

    # OpenCV VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_path, fourcc, FPS, (WIDTH, HEIGHT), isColor=False)

    for i in range(num_frames):
        start = i * frame_size
        end = start + frame_size

        frame = np.frombuffer(raw_data[start:end], dtype=np.uint8)
        frame = frame.reshape((HEIGHT, WIDTH))

        writer.write(frame)

    writer.release()
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--take_dir", required=True)

    args = parser.parse_args()

    left_raw = os.path.join(args.take_dir, "left.raw8")
    right_raw = os.path.join(args.take_dir, "right.raw8")

    raw_to_video(left_raw, os.path.join(args.take_dir, "left.mp4"))
    raw_to_video(right_raw, os.path.join(args.take_dir, "right.mp4"))
