"""Pruebas de instanciación e integridad de los widgets base reutilizables."""

from pytestqt.qtbot import QtBot

from app.widgets import (
    DangerButton,
    InfoCard,
    PrimaryButton,
    StatCard,
    StepHeader,
    WarningBanner,
)


def test_stat_card_widget(qtbot: QtBot) -> None:
    card = StatCard(title="Filas", value="1,000")
    qtbot.addWidget(card)

    assert card.title_label.text() == "Filas"
    assert card.value_label.text() == "1,000"

    card.set_value("2,500")
    assert card.value_label.text() == "2,500"


def test_info_card_widget(qtbot: QtBot) -> None:
    card = InfoCard(title="Archivo", content="sample.csv")
    qtbot.addWidget(card)

    assert card.title_label.text() == "Archivo"
    assert card.content_label.text() == "sample.csv"

    card.set_content("otro.parquet")
    assert card.content_label.text() == "otro.parquet"


def test_warning_banner_widget(qtbot: QtBot) -> None:
    banner = WarningBanner(message="Atención con los datos")
    qtbot.addWidget(banner)

    assert "Atención con los datos" in banner.message_label.text()
    banner.set_message("Nuevo aviso")
    assert banner.message_label.text() == "Nuevo aviso"


def test_step_header_widget(qtbot: QtBot) -> None:
    header = StepHeader(step_number=1, title="Cargar datos")
    qtbot.addWidget(header)

    assert header.badge.text() == "1"
    assert header.title_label.text() == "Cargar datos"

    header.set_title("Información general")
    assert header.title_label.text() == "Información general"


def test_buttons_widget(qtbot: QtBot) -> None:
    primary = PrimaryButton("Aceptar")
    danger = DangerButton("Eliminar registros")
    qtbot.addWidget(primary)
    qtbot.addWidget(danger)

    assert primary.text() == "Aceptar"
    assert primary.objectName() == "primaryButton"

    assert danger.text() == "Eliminar registros"
    assert danger.objectName() == "dangerButton"
