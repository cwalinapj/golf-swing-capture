def load_sequence(video_path, num_frames=16):
    cap = cv2.VideoCapture(video_path)

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    center = total // 2
    start = max(0, center - num_frames // 2)

    frames = []

    for i in range(start, start + num_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()

        if ret:
            frame = cv2.resize(frame, (224, 224))
            frame = frame / 255.0
            frame = torch.tensor(frame).permute(2, 0, 1).float()
            frames.append(frame)

    cap.release()

    return torch.stack(frames)  # (T, C, H, W)
