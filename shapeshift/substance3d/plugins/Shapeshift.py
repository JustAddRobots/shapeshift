#!/usr/bin/env python3

import importlib
from PySide2.QtWidgets import QMenu
import substance_painter.ui as painter_ui

from shapeshift.substance3d.modules import create
from shapeshift.substance3d.modules import export


plugin_widgets = []
plugin_loggers = []


def start_plugin():
    app_menu = QMenu(parent=painter_ui.get_main_window())
    app_menu.setTitle("Shapeshift")
    create_dialog = create.CreateDialog()
    export_dialog = export.ExportDialog()
    app_menu.addAction(create_dialog.create_action)
    app_menu.addAction(export_dialog.export_action)
    painter_ui.add_menu(
        app_menu
    )
    plugin_widgets.append(app_menu)
    plugin_widgets.append(export_dialog)
    plugin_widgets.append(create_dialog)
    plugin_loggers.append(create_dialog.logger)
    plugin_loggers.append(export_dialog.logger)
    return None


def close_plugin():
    for logger in plugin_loggers:
        for handler in logger.handlers:
            logger.removeHandler(handler)
    plugin_loggers.clear()

    for widget in plugin_widgets:
        painter_ui.delete_ui_element(widget)
    plugin_widgets.clear()

    return None


def reload_plugin():
    deps = [
        create,
        export
    ]
    for dep in deps:
        importlib.reload(dep)

    return None


if __name__ == "__main__":
    start_plugin()
