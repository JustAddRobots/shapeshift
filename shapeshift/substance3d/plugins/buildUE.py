#!/usr/bin/env python3

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
    QPlainTextEdit,
    QPushButton,
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

import substance_painter.event as painter_ev
import substance_painter.exception as painter_exc
import substance_painter.logging as painter_log
import substance_painter.ui as painter_ui
import substance_painter.project as painter_proj
from shapeshift.substance3d.modules import baketools

plugin_widgets = []


class Worker(QObject):
    finished = Signal()
    result = Signal(object)

    def __init__(self):
        super(Worker, self).__init__()

    @Slot()
    def run(self, mesh_file_path, texture_res):
        mm = baketools.MeshMap(mesh_file_path, texture_res)
        dict_ = mm.get_baked_mesh_maps()
        self.result.emit(dict_)


class ShapeshiftDialog(QDialog, QPlainTextEdit):

    def __init__(self):
        # super().__init__()
        # super(ShapeshiftMenu, self).__init__("Shapeshift", parent=None)
        super().__init__(parent=painter_ui.get_main_window())
        self.init_UI()

    def init_UI(self):
        # self.app_menu = QMenu(parent=painter_ui.get_main_window())
        self.app_menu = QMenu(parent=self)
        self.app_menu.setTitle("Shapeshift")
        self.create_action = QWidgetAction(self)
        self.create_action.setText("Create UE Project...")
        self.create_action.triggered.connect(self.create_project)
        self.app_menu.addAction(self.create_action)

        self.setWindowTitle("Create UE Project")

        self.create_button = QPushButton("Create", self)
        self.create_button.setEnabled(False)
        self.create_button.setDefault(False)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setEnabled(True)
        self.cancel_button.setDefault(True)
        self.button_box = QDialogButtonBox(self)
        self.button_box.addButton(self.create_button, QDialogButtonBox.AcceptRole)
        self.button_box.addButton(self.cancel_button, QDialogButtonBox.RejectRole)
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
        self.bake_checkbox.setCheckState(Qt.Checked)
        self.mesh_map_spacer = QSpacerItem(60, 0)
        self.texture_res_box = QComboBox(parent=self)
        self.texture_res_box.addItems([
            "256",
            "512",
            "1024",
            "2048",
            "4096"
        ])
        self.texture_res_box.setCurrentIndex(3)
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

        self.button_box.accepted.connect(self.create_project)
        self.button_box.rejected.connect(self.reject)
        self.mesh_file_button.clicked.connect(self.on_mesh_file_button_clicked)
        self.mesh_file_line.editingFinished.connect(self.on_mesh_file_line_edited)
        self.bake_checkbox.stateChanged.connect(self.on_bake_checkbox_changed)

        painter_ev.DISPATCHER.connect(
            painter_ev.ProjectEditionEntered,
            self.on_project_edition_entered
        )

    def on_project_edition_entered(self, ev):
        self.bake_maps()

    def enable_buttons(self, mesh_file_path):
        p = Path(mesh_file_path)
        if mesh_file_path and p.exists():
            self.mesh_file_line.setText(mesh_file_path)
            self.create_button.setEnabled(True)
            self.create_button.setDefault(True)
            self.cancel_button.setDefault(False)

    def on_mesh_file_line_edited(self):
        self.enable_buttons(self.mesh_file_line.text())

    def on_mesh_file_button_clicked(self):
        mesh_file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Static Mesh",
            str(Path.home()),
            "Static Mesh Files (*.fbx)"
        )
        self.enable_buttons(mesh_file_path)

    def on_bake_checkbox_changed(self):
        if self.bake_checkbox.isChecked():
            self.texture_res_box.setEnabled(True)
        else:
            self.texture_res_box.setEnabled(False)

    def get_dialog_vars(self):
        vars = {}
        vars["mesh_file_path"] = self.mesh_file_line.text()

        if self.bake_checkbox.checkState() == Qt.CheckState.Checked:
            vars["is_bake_maps_checked"] = True
        elif self.bake_checkbox.checkState() == Qt.CheckState.Unchecked:
            vars["is_bake_maps_checked"] = False

        try:
            texture_res = int(self.texture_res_box.currentText())
        except ValueError as e:
            painter_log.log(
                painter_log.ERROR,
                "shapeshift",
                f"Texture Resolution Error: {e}"
            )
        else:
            vars["texture_res"] = texture_res

        return vars

    def get_project_settings(self, mesh_file_path, texture_res):
        texture_dir_path = str(Path(mesh_file_path).parent).replace(
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

    @Slot()
    def create_project(self):
        vars = self.get_dialog_vars()
        project_settings = self.get_project_settings(
            vars["mesh_file_path"],
            vars["texture_res"]
        )
        if painter_proj.is_open():
            painter_log.log(
                painter_log.ERROR,
                "shapeshift",
                f"Project Already Open Error: {painter_proj.name()}"
            )
        else:
            try:
                painter_proj.create(
                    vars["mesh_file_path"],
                    # template_file_path=
                    settings=project_settings
                )
            except (painter_exc.ProjectError, ValueError) as e:
                painter_log.log(
                    painter_log.ERROR,
                    "shapeshift",
                    f"Project Creation Error: {e}"
                )

    def bake_maps_inline(self):
        mm = baketools.MeshMap(self.mesh_file_line.text())
        d = mm.get_baked_mesh_maps()
        self.log_maps(d)

    def bake_maps(self):
        vars = self.get_dialog_vars()
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(
            lambda: self.worker.run(vars["mesh_file_path"], vars["texture_res"])
        )
        self.worker.finished.connect(self.thread.quit)
        self.worker.result.connect(self.log_maps)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    @Slot()
    def log_maps(self, d):
        painter_log.log(
            painter_log.INFO,
            "shapeshift",
            pprint.saferepr(d)
        )

#         if dialog.exec_():
#             painter_log.log(
#                 painter_log.INFO,
#                 "shapeshift",
#                 (
#                     f"OK: "
#                     f"mesh_file_path: {dialog.mesh_file_line.text()} "
#                     f"bake_checkbox: {dialog.bake_checkbox.checkState()} "
#                     f"texture_res_box: {dialog.texture_res_box.currentText()} "
#                 )
#             )
#         else:
#             painter_log.log(
#                 painter_log.INFO,
#                 "shapeshift",
#                 "Cancel"
#             )


# class ShapeshiftMenu(QMenu):
#
#     def __init__(self):
#         super(ShapeshiftMenu, self).__init__("Shapeshift", parent=None)
#         self._mesh_file_path = ""
#
#         create_ue = QWidgetAction(self)
#         create_ue.setText("Create UE Project...")
#         # create_ue.triggered.connect(self._create_project)
#         create_ue.triggered.connect(self.create_project)
#         self.addAction(create_ue)

#     def create_project(self):
#         # dialog = QDialog(parent=painter_ui.get_main_window())
#         dialog = CreateUEDialog()
#         if dialog.exec_():
#             painter_log.log(
#                 painter_log.INFO,
#                 "shapeshift",
#                 (
#                     f"OK: "
#                     f"mesh_file_path: {dialog.mesh_file_line.text()} "
#                     f"bake_checkbox: {dialog.bake_checkbox.checkState()} "
#                     f"texture_res_box: {dialog.texture_res_box.currentText()} "
#                 )
#             )
#         else:
#             painter_log.log(
#                 painter_log.INFO,
#                 "shapeshift",
#                 "Cancel"
#             )

#     def _create_project(self):
#         texture_res = CONSTANTS().TEXTURE_RES
#         self._mesh_file_path = self._get_mesh_file_path()
#         if self._mesh_file_path:
#             project_settings = self._get_project_settings(
#                 self._mesh_file_path,
#                 texture_res
#             )
#             try:
#                 painter_proj.create(
#                     self._mesh_file_path,
#                     # template_file_path=
#                     settings=project_settings
#                 )
#             except (painter_exc.ProjectError, ValueError) as e:
#                 painter_log.log(
#                     painter_log.ERROR,
#                     "shapeshift",
#                     f"Project Creation Error: {e}"
#                 )
#             else:
#                 self.thread = QThread()
#                 self.worker = Worker()
#                 self.worker.moveToThread(self.thread)
#                 self.thread.started.connect(lambda: self.worker.run(self._mesh_file_path))
#                 self.worker.finished.connect(self.thread.quit)
#                 self.worker.result.connect(self.log_maps)
#                 self.worker.finished.connect(self.worker.deleteLater)
#                 self.thread.start()
#         return None

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

#     @Slot()
#     def log_maps(self, d):
#         painter_log.log(
#             painter_log.INFO,
#             "shapeshift",
#             pprint.saferepr(d)
#         )

#     def _get_mesh_file_path(self):
#         mesh_file_path, _ = QFileDialog.getOpenFileName(
#             self,
#             "Open Static Mesh",
#             str(Path.home()),
#             "Static Mesh Files (*.fbx)"
#         )
#         if not mesh_file_path:
#             painter_log.log(
#                 painter_log.ERROR,
#                 "shapeshift",
#                 "No mesh file selected"
#             )
#         return mesh_file_path

#     def _get_project_settings(self, mesh_file_path, texture_res):
#         texture_dir_path = os.path.dirname(mesh_file_path).replace(
#             "Meshes",
#             "Textures"
#         )
#         project_settings = painter_proj.Settings(
#             # default_save_path
#             default_texture_resolution=texture_res,
#             export_path=texture_dir_path,
#             import_cameras=False,
#             normal_map_format=painter_proj.NormalMapFormat.DirectX,
#             tangent_space_mode=painter_proj.TangentSpace.PerFragment
#         )
#         return project_settings


def start_plugin():
    shapeshift_dialog = ShapeshiftDialog()
    painter_ui.add_menu(
        shapeshift_dialog.app_menu
    )
    plugin_widgets.append(shapeshift_dialog)
    return None


def close_plugin():
    for widget in plugin_widgets:
        painter_ui.delete_ui_element(widget)

    plugin_widgets.clear()
    return None


if __name__ == "__main__":
    start_plugin()
