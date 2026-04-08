from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Union


def log_training_run(log_path: Union[str, Path], payload: Dict) -> Path:
    """Use Case 13: Log model training runs for reproducibility."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    return path
