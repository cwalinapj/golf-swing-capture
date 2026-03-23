"""Entry point for the Golf Swing Capture application."""

from capture.config import Config
from capture.web import create_app


def main():
    config = Config()
    app = create_app(config)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


if __name__ == "__main__":
    main()
