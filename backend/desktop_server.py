"""PyInstaller entry point; configure paths before importing the application."""
import argparse
import multiprocessing


def main():
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    import uvicorn
    from lab.main import app
    uvicorn.run(app, host="127.0.0.1", port=args.port, ws="websockets", ws_max_size=8388608, log_level="info")


if __name__ == "__main__":
    main()
