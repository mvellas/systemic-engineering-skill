"""Bounded subprocess for local numerical engines; output contains only structured results."""

from pathlib import Path
import json, sys, socket

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sef_runtime import engines, predictive


def deny(*args, **kwargs):
    raise RuntimeError("Local executor blocks network access.")


def main():
    request = json.load(sys.stdin)
    c = request["config"]
    project = request["project"]
    socket.create_connection = deny
    socket.socket.connect = deny
    if c["engine"] in {"monte-carlo", "agents", "dynamics"}:
        result = engines.business(c)
    elif c["engine"] == "failure":
        result = engines.failure(c)
    elif c["engine"] == "mcmc":
        result = engines.mcmc(c)
    else:
        result = getattr(predictive, c["engine"])(project, c)
    print(
        json.dumps({"ok": True, "result": result}, ensure_ascii=False, allow_nan=False)
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "type": type(error).__name__,
                    "message": str(error)
                    if isinstance(error, ValueError)
                    else "Local engine failed",
                }
            )
        )
        sys.exit(1)
