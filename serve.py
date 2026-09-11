"""Start the app with no console attached.

Launched by run.bat through pythonw.exe, so there is no window to close and
nothing dies when the launcher exits. Writes its own PID and log, which is
how stop.bat finds it again.

    python serve.py api      FastAPI - the domain. Start this FIRST.
    python serve.py ui       Streamlit  - what people open.

The UI talks to the API over HTTP and holds no domain code, so the API has to
be up first. run.bat does that ordering.
"""

from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
LOGS = ROOT / "logs"


def _detach(name: str) -> None:
    os.chdir(ROOT)
    LOGS.mkdir(exist_ok=True)
    # pythonw has no stdout at all; without this, anything that prints raises.
    log = open(LOGS / f"{name}.log", "a", buffering=1, encoding="utf-8")
    sys.stdout = sys.stderr = log
    (LOGS / f"{name}.pid").write_text(str(os.getpid()), encoding="utf-8")


def run_ui() -> None:
    _detach("server")
    port = os.getenv("LIFTSIM_PORT", "8501")
    host = os.getenv("LIFTSIM_HOST", "127.0.0.1")
    sys.argv = ["streamlit", "run", str(ROOT / "app.py"),
                "--server.port", port, "--server.address", host,
                "--server.headless", "true", "--browser.gatherUsageStats", "false"]
    from streamlit.web.cli import main
    main()


def run_api() -> None:
    _detach("api")
    import uvicorn
    uvicorn.run("api.main:app", host=os.getenv("LIFTSIM_HOST", "127.0.0.1"),
                port=int(os.getenv("LIFTSIM_API_PORT", "8000")), log_config=None)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "ui"
    {"api": run_api, "ui": run_ui}[mode]()
