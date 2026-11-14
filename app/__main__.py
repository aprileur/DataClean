"""Punto de entrada para ejecución directa con `python -m app`.

El orden importa: primero se configura el logging y el borde de errores, después
se crea la `QApplication`. La variable `QT_ENABLE_HIGHDPI_SCALING` documenta el
soporte HiDPI (en Qt 6 el escalado es automático, pero se fija por portabilidad).
"""

import os
import sys


def main() -> int:
    """Configura el entorno y arranca la ventana principal."""
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    from app.logging_config import setup_logging
    from app.main_window import main as run_app
    from app.ui.error_boundary import handle_exception

    setup_logging()
    sys.excepthook = handle_exception
    return run_app()


if __name__ == "__main__":
    sys.exit(main())
