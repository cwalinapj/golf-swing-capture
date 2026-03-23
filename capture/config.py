"""Configuration settings for the golf swing capture application."""

import os


class Config:
    """Application configuration."""

    # Camera settings
    CAMERA_INDEX: int = int(os.environ.get("CAMERA_INDEX", 0))
    FRAME_WIDTH: int = int(os.environ.get("FRAME_WIDTH", 1280))
    FRAME_HEIGHT: int = int(os.environ.get("FRAME_HEIGHT", 720))
    FPS: int = int(os.environ.get("FPS", 30))

    # Recording settings
    OUTPUT_DIR: str = os.environ.get("OUTPUT_DIR", "recordings")
    VIDEO_CODEC: str = os.environ.get("VIDEO_CODEC", "mp4v")
    VIDEO_EXTENSION: str = ".mp4"

    # Web server settings
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", 5000))
    DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"
