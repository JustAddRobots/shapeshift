#!/usr/bin/env python3

import os.path
import pprint
from pathlib import Path

from PySide2.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QSpacerItem,
    QToolButton,
    QVBoxLayout,
    QWidgetAction,
)
from PySide2.QtCore import (
    QObject,
    Qt,
    QThread,
    Signal,
    Slot,
)

import substance_painter.exception as painter_exc
import substance_painter.logging as painter_log
import substance_painter.ui as painter_ui
import substance_painter.project as painter_proj

from shapeshift.substance3d.modules import baketools
from shapeshift.common.constants import _const as CONSTANTS

plugin_widgets = []


class Worker(QObject):
    finished = Signal()
    result = Signal(object)

    def __init__(self):
        super(Worker, self).__init__()

    @Slot()
    def run(self, mesh_file_path):
        mm = baketools.MeshMap(mesh_file_path)
        d = mm.get_baked_mesh_maps()
        self.result.emit(d)


class CreateUEDialog(QDialog):

    def __init__(self):
        super().__init__(parent=painter_ui.get_main_window())

        self.setWindowTitle("Create UE Project")
        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.button_box = QDialogButtonBox(buttons)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box_spacer = QSpacerItem(0, 20)

        self.main_layout = QVBoxLayout(self)

        self.mesh_file_layout = QHBoxLayout(self)
        self.mesh_file_label = QLabel(self)
        self.mesh_file_label.setText("Mesh File")
        self.mesh_file_label.setAlignment(Qt.AlignLeft)
        self.mesh_file_line = QLineEdit(self)
        self.mesh_file_button = QToolButton(self)
        self.mesh_file_label.setBuddy(self.mesh_file_line)

        self.mesh_file_layout.addWidget(self.mesh_file_line)
        self.mesh_file_layout.addWidget(self.mesh_file_button)

        self.mesh_map_layout = QHBoxLayout(self)
        self.bake_checkbox = QCheckBox("Bake Mesh Maps", self)
        self.bake_checkbox.setCheckState(Qt.Checked)  # isChecked()
        self.mesh_map_spacer = QSpacerItem(60, 0)
        self.texture_res_box = QComboBox(parent=self)
        self.texture_res_box.addItems([
            "256",
            "512",
            "1024",
            "2048",
            "4096"
        ])
        self.texture_res_box.setCurrentIndex(2)
        self.texture_res_label = QLabel(self)
        self.texture_res_label.setText("Texture Resolution")
        self.texture_res_label.setBuddy(self.texture_res_box)

        self.mesh_map_layout.addWidget(self.bake_checkbox)
        self.mesh_map_layout.addSpacerItem(self.mesh_map_spacer)
        self.mesh_map_layout.addWidget(self.texture_res_label)
        self.mesh_map_layout.addWidget(self.texture_res_box)

        self.main_layout.addWidget(self.mesh_file_label)
        self.main_layout.addLayout(self.mesh_file_layout)
        self.main_layout.addLayout(self.mesh_map_layout)
        self.main_layout.addSpacerItem(self.button_box_spacer)
        self.main_layout.addWidget(self.button_box)
        self.setLayout(self.main_layout)


class ShapeshiftMenu(QMenu):

    def __init__(self):
        super(ShapeshiftMenu, self).__init__("Shapeshift", parent=None)
        self._mesh_file_path = ""

        create_ue = QWidgetAction(self)
        create_ue.setText("Create UE Project...")
        # create_ue.triggered.connect(self._create_project)
        create_ue.triggered.connect(self.create_project)
        self.addAction(create_ue)

    def create_project(self):
        # dialog = QDialog(parent=painter_ui.get_main_window())
        dialog = CreateUEDialog()
        if dialog.exec_():
            painter_log.log(
                painter_log.INFO,
                "shapeshift",
                "OK"
            )
        else:
            painter_log.log(
                painter_log.INFO,
                "shapeshift",
                "Cancel"
            )

    def _create_project(self):
        texture_res = CONSTANTS().TEXTURE_RES
        self._mesh_file_path = self._get_mesh_file_path()
        if self._mesh_file_path:
            project_settings = self._get_project_settings(
                self._mesh_file_path,
                texture_res
            )
            try:
                painter_proj.create(
                    self._mesh_file_path,
                    # template_file_path=
                    settings=project_settings
                )
            except (painter_exc.ProjectError, ValueError) as e:
                painter_log.log(
                    painter_log.ERROR,
                    "shapeshift",
                    f"Project Creation Error: {e}"
                )
            else:
                self.thread = QThread()
                self.worker = Worker()
                self.worker.moveToThread(self.thread)
                self.thread.started.connect(lambda: self.worker.run(self._mesh_file_path))
                self.worker.finished.connect(self.thread.quit)
                self.worker.result.connect(self.log_maps)
                self.worker.finished.connect(self.worker.deleteLater)
                self.thread.start()
        return None

#     def _bake_maps(self):
#         self.thread = QThread()
#         self.worker = Worker()
#         self.worker.moveToThread(self.thread)
#         self.thread.started.connect(lambda: self.worker.run(self._mesh_file_path))
#         self.worker.finished.connect(self.thread.quit)
#         self.worker.result.connect(self.log_maps)
#         self.worker.finished.connect(self.worker.deleteLater)
#         self.thread.finished.connect(self.thread.deleteLater)
#         self.thread.start()
#         return None

    @Slot()
    def log_maps(self, d):
        painter_log.log(
            painter_log.INFO,
            "shapeshift",
            pprint.saferepr(d)
        )

    def _get_mesh_file_path(self):
        mesh_file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Static Mesh",
            str(Path.home()),
            "Static Mesh Files (*.fbx)"
        )
        if not mesh_file_path:
            painter_log.log(
                painter_log.ERROR,
                "shapeshift",
                "No mesh file selected"
            )
        return mesh_file_path

    def _get_project_settings(self, mesh_file_path, texture_res):
        texture_dir_path = os.path.dirname(mesh_file_path).replace(
            "Meshes",
            "Textures"
        )
        project_settings = painter_proj.Settings(
            # default_save_path
            default_texture_resolution=texture_res,
            export_path=texture_dir_path,
            import_cameras=False,
            normal_map_format=painter_proj.NormalMapFormat.DirectX,
            tangent_space_mode=painter_proj.TangentSpace.PerFragment
        )
        return project_settings


def start_plugin():
    shapeshift_menu = ShapeshiftMenu()
    painter_ui.add_menu(
        shapeshift_menu
    )
    plugin_widgets.append(shapeshift_menu)
    return None


def close_plugin():
    for widget in plugin_widgets:
        painter_ui.delete_ui_element(widget)

    plugin_widgets.clear()
    return None


if __name__ == "__main__":
    start_plugin()
