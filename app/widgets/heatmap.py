"""Widget de mapa de calor de datos faltantes basado en matplotlib QtAgg."""

from __future__ import annotations

import matplotlib
from PySide6.QtWidgets import QSizePolicy

matplotlib.use("QtAgg")

import pandas as pd  # noqa: E402
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402


class MissingDataHeatmap(FigureCanvasQTAgg):
    """Canvas de matplotlib para visualizar el mapa de calor de datos faltantes."""

    def __init__(self, parent=None, width: float = 6.0, height: float = 4.0, dpi: int = 100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Colormap: 0=Presente (#93C5FD), 1=Faltante (#F472B6)
        self.cmap = ListedColormap(["#93C5FD", "#F472B6"])
        self.has_data = False

    def set_data(
        self,
        mask: pd.DataFrame,
        is_sample: bool = False,
        total_rows: int | None = None,
    ) -> None:
        """Dibuja el mapa de calor de faltantes sobre el canvas."""
        self.axes.clear()

        if mask.empty or len(mask.columns) == 0:
            self.axes.text(
                0.5,
                0.5,
                "Sin datos disponibles para visualizar",
                ha="center",
                va="center",
                fontsize=11,
                color="#6B7280",
                transform=self.axes.transAxes,
            )
            self.axes.axis("off")
            self.fig.tight_layout()
            self.draw()
            self.has_data = False
            return

        # Matriz booleana numérica: 0 = presente, 1 = faltante
        data_matrix = mask.astype(int).values

        # Mostrar imagen
        self.axes.imshow(
            data_matrix,
            cmap=self.cmap,
            aspect="auto",
            interpolation="nearest",
            vmin=0,
            vmax=1,
        )

        # Configurar ejes
        cols = list(mask.columns)
        self.axes.set_xticks(range(len(cols)))
        self.axes.set_xticklabels(cols, rotation=45, ha="right", fontsize=9)

        # Eje Y: mostrar hasta 10 marcas de fila representativas
        n_rows = len(mask)
        step = max(1, n_rows // 10)
        y_ticks = list(range(0, n_rows, step))
        self.axes.set_yticks(y_ticks)
        self.axes.set_yticklabels([str(mask.index[i]) for i in y_ticks], fontsize=8)

        # Título y aviso de muestreo
        title = "Mapa de datos faltantes"
        if is_sample:
            rows_shown = len(mask)
            total_str = f" de {total_rows:,}" if total_rows else ""
            title += f" (Muestra representativa de {rows_shown:,}{total_str} registros)"
        self.axes.set_title(title, fontsize=11, fontweight="bold", pad=10, color="#1F2937")

        # Leyenda
        legend_elements = [
            Patch(facecolor="#93C5FD", edgecolor="#60A5FA", label="Presente"),
            Patch(facecolor="#F472B6", edgecolor="#EC4899", label="Faltante"),
        ]
        self.axes.legend(
            handles=legend_elements,
            loc="upper right",
            bbox_to_anchor=(1.0, 1.15),
            ncol=2,
            frameon=False,
            fontsize=9,
        )

        self.fig.tight_layout()
        self.draw()
        self.has_data = True

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Redibuja ajustando tight_layout al redimensionar la ventana."""
        super().resizeEvent(event)
        try:
            self.fig.tight_layout()
            self.draw_idle()
        except Exception:
            pass

    def clear(self) -> None:
        """Limpia el gráfico."""
        self.axes.clear()
        self.axes.axis("off")
        self.draw()
        self.has_data = False
