"""Entrypoint para el ejecutable de DataClean."""

import sys
from pathlib import Path

# Garantizar que la raíz del proyecto esté en sys.path si se ejecuta como script suelto
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.main_window import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
