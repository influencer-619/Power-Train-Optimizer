from __future__ import annotations

import logging
import os
import sys

from backend.paths import data_dir


def setup_logging() -> logging.Logger:
    # Windowed EXE: stdout/stderr may be None
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")

    log_path = data_dir() / "logs" / "powertrain.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("powertrain")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    try:
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    except Exception:
        pass
    return logger
