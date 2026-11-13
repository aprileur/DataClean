"""Módulo de gestión del tema visual (QSS) de DataClean."""

from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget


def load_stylesheet() -> str:
    """Lee y retorna el contenido del archivo de estilos theme.qss."""
    qss_path = Path(__file__).parent / "theme.qss"
    if not qss_path.exists():
        return ""
    with open(qss_path, encoding="utf-8") as f:
        return f.read()


def apply_theme(target: QApplication | QWidget) -> None:
    """Aplica la hoja de estilos centralizada a la aplicación o widget."""
    qss = load_stylesheet()
    if qss:
        target.setStyleSheet(qss)
