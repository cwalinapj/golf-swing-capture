
import cv2
import numpy as np

def detect_impacts(video_path, min_gap_frames=30):
    cap = cv2.VideoCapture(video_path)

    prev = None
    motion_scores = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = frame.astype(np.float32)

        if prev is not None:
            diff = np.abs(frame - prev)
            score = np.sum(diff)
        else:
            score = 0

        motion_scores.append(score)
        prev = frame

    cap.release()

    motion_scores = np.array(motion_scores)

    # Normalize
    threshold = np.mean(motion_scores) + 3 * np.std(motion_scores)

    peaks = []
    last_peak = -min_gap_frames

    for i, val in enumerate(motion_scores):
        if val > threshold and (i - last_peak) > min_gap_frames:
            peaks.append(i)
            last_peak = i

    print(f"Detected {len(peaks)} swings")
    return peaks
