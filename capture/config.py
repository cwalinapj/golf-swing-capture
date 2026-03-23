from datetime import datetime


MONO_W = 640
MONO_H = 400
MONO_FPS = 117

RGB_W = 1920
RGB_H = 1080
RGB_FPS = 35

DEFAULT_MONO_EXPOSURE_US = 120
DEFAULT_MONO_ISO = 400
DEFAULT_RGB_EXPOSURE_US = 120
DEFAULT_RGB_ISO = 200
DEFAULT_RGB_FOCUS = 120


def now_local():
    return datetime.now().astimezone()


def ts_for_name(dt: datetime) -> str:
    return dt.strftime("%Y%m%d_%H%M%S_%f")[:-3]


def iso_ts(dt: datetime) -> str:
    return dt.isoformat()
