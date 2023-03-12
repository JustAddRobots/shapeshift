#!/usr/bin/env python3

import copy
import importlib
import logging
import math
import pprint
import time
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
    QTreeWidget,
    QTreeWidgetItem,
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
# from PySide2.QtGui import QIcon

import substance_painter.event as painter_ev
import substance_painter.exception as painter_exc
import substance_painter.export as painter_exp
import substance_painter.logging as painter_log
import substance_painter.project as painter_proj
import substance_painter.textureset as painter_tex
import substance_painter.ui as painter_ui
from shapeshift.substance3d.modules import baketools
from shapeshift.substance3d.modules import importtools

plugin_widgets = []


class QPlainTextEditLogger(QObject):
    append = Signal(str)

    def __init__(self, parent):
        super().__init__()
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.widget.setFixedHeight(100)
        self.widget.setBackgroundVisible(False)
        self.append.connect(self.widget.appendPlainText)


class QLogHandler(logging.Handler):

    def __init__(self, emitter):
        super().__init__()
        self._emitter = emitter

    @property
    def emitter(self):
        return self._emitter

    def emit(self, record):
        msg = self.format(record)
        self.emitter.append.emit(msg)


class Baker(QObject):
    finished = Signal()
    result = Signal(object)

    def __init__(self, mesh_file_path, texture_res, **kwargs):
        super(Baker, self).__init__()
        self._extra_handler = kwargs.setdefault("extra_handler", None)
        self._mm = baketools.MeshMap(
            mesh_file_path,
            texture_res,
            extra_handler=self._extra_handler,
        )
        self._bake_log = f"{self._mm.tmp_bake_dir}/log.txt"

    @property
    def bake_log(self):
        return self._bake_log

    @Slot()
    def run(self):
        dict_ = self._mm.get_baked_mesh_maps()
        self.result.emit(dict_)
        self.finished.emit()


class Importer(QObject):
    finished = Signal()

    def __init__(self, mesh_file_path, mesh_maps, **kwargs):
        super(Importer, self).__init__()
        self._extra_handler = kwargs.setdefault("extra_handler", None)
        self._texset = importtools.TexSet(
            mesh_file_path,
            mesh_maps,
            extra_handler=self._extra_handler,
        )

    @Slot()
    def run(self):
        self._texset.import_mesh_maps()
        self.finished.emit()


export_config = {
    "exportShaderParams": False,
    "exportParameters": [
        {
            "parameters": {
                "fileFormat": "tga",
                "bitDepth": "8",
                "dithering": False,
                "paddingAlgorithm": "infinite"
            }
        }
    ],
    "exportPresets": [
        {
            "name": "Shapeshift",
            "maps": [
                {
                    "fileName": "T_$textureSet_D",
                    "channels": [
                        {
                            "destChannel": "L",
                            "srcChannel": "L",
                            "srcMapType": "documentMap",
                            "srcMapName": "basecolor"
                        }
                    ]
                },
                {
                    "fileName": "T_$textureSet_M",
                    "channels": [
                        {
                            "destChannel": "R",
                            "srcChannel": "L",
                            "srcMapType": "meshMap",
                            "srcMapName": "ambient_occlusion"
                        },
                        {
                            "destChannel": "G",
                            "srcChannel": "L",
                            "srcMapType": "documentMap",
                            "srcMapName": "roughness"
                        },
                        {
                            "destChannel": "B",
                            "srcChannel": "L",
                            "srcMapType": "documentMap",
                            "srcMapName": "metallic"
                        }
                    ]
                },
                {
                    "fileName": "T_$textureSet_N",
                    "channels": [
                        {
                            "destChannel": "L",
                            "srcChannel": "L",
                            "srcMapType": "meshMap",
                            "srcMapName": "normal_base"
                        }
                    ],
                    "parameter": {
                        "dithering": True
                    }
                }
            ]
        }
    ]
}


class ExportDialog(QDialog):

    def __init__(self):
        super(ExportDialog, self).__init__(parent=painter_ui.get_main_window())
        self.init_UI()

    def init_UI(self):
        self.export_action = QWidgetAction(self)
        self.export_action.setText("Export UE Project...")
        self.export_action.triggered.connect(self.exec_)

        self.setWindowTitle("Export UE Project")

        self.export_button = QPushButton("Export", parent=self)
        self.export_button.setEnabled(False)
        self.export_button.setDefault(False)
        self.cancel_button = QPushButton("Cancel", parent=self)
        self.cancel_button.setEnabled(True)
        self.cancel_button.setDefault(True)
        self.button_box = QDialogButtonBox(parent=self)
        self.button_box.addButton(self.export_button, QDialogButtonBox.AcceptRole)
        self.button_box.addButton(self.cancel_button, QDialogButtonBox.RejectRole)

        self.main_layout = QVBoxLayout(self)

        self.export_dir_layout = QHBoxLayout(self)
        self.export_dir_label = QLabel(parent=self)
        self.export_dir_label.setText("Export Directory")
        self.export_dir_label.setAlignment(Qt.AlignLeft)
        self.export_dir_line = QLineEdit(parent=self)
        self.export_dir_button = QToolButton(parent=self)
        # self.export_dir_button.setIcon(QIcon("SP_DialogOpenButton"))
        self.export_dir_label.setBuddy(self.export_dir_line)
        self.export_dir_start_path = str(Path.home())

        self.export_dir_layout.addWidget(self.export_dir_line)
        self.export_dir_layout.addWidget(self.export_dir_button)

        self.override_param_layout = QHBoxLayout(self)
        self.file_type_box = QComboBox(parent=self)
        self.file_type_box.addItems([
            "tga",
            "png",
        ])
        self.file_type_box.setCurrentIndex(0)
        self.file_type_label = QLabel(parent=self)
        self.file_type_label.setText("File Type")
        self.file_type_label.setBuddy(self.file_type_box)

        self.override_param_spacer = QSpacerItem(120, 0)

        self.texture_res_box = QComboBox(parent=self)
        self.texture_res_box.addItems([
            "Current",
            "256",
            "512",
            "1024",
            "2048",
            "4096",
            "8192",
        ])
        self.texture_res_box.setCurrentIndex(0)
        self.texture_res_label = QLabel(parent=self)
        self.texture_res_label.setText("Texture Resolution")
        self.texture_res_label.setBuddy(self.texture_res_box)

        self.override_param_layout.addWidget(self.file_type_label)
        self.override_param_layout.addWidget(self.file_type_box)
        self.override_param_layout.addSpacerItem(self.override_param_spacer)
        self.override_param_layout.addWidget(self.texture_res_label)
        self.override_param_layout.addWidget(self.texture_res_box)

        self.export_tree = QTreeWidget()
        self.export_tree.setColumnCount(2)
        self.export_tree.setFixedHeight(100)
        self.export_tree.setHeaderLabels(["Texture", "Resolution"])
        self.export_tree.setColumnWidth(0, 300)
        self.export_tree_label = QLabel(parent=self)
        self.export_tree_label.setText("Exports")
        self.export_tree_label.setBuddy(self.export_tree)

        # self.export_list_box = QPlainTextEdit(self)
        # self.export_list_box.setReadOnly(True)
        # self.export_list_box.setFixedHeight(100)
        # self.export_list_label = QLabel(parent=self)
        # self.export_list_label.setText("Export List")
        # self.export_list_label.setBuddy(self.export_list_box)

        self.logbox = QPlainTextEditLogger(self)
        self.logbox_label = QLabel(parent=self)
        self.logbox_label.setText("Logs")
        self.logbox_label.setBuddy(self.logbox.widget)

        self.logbox_handler = QLogHandler(self.logbox)
        self.logger = logging.getLogger()
        self.logger.addHandler(self.logbox_handler)
        self.logger.setLevel(logging.DEBUG)

        self.main_layout.addWidget(self.export_dir_label)
        self.main_layout.addLayout(self.export_dir_layout)
        self.main_layout.addLayout(self.override_param_layout)
        # self.main_layout.addWidget(self.export_list_label)
        # self.main_layout.addWidget(self.export_list_box)
        self.main_layout.addWidget(self.export_tree_label)
        self.main_layout.addWidget(self.export_tree)
        self.main_layout.addWidget(self.logbox_label)
        self.main_layout.addWidget(self.logbox.widget)
        self.main_layout.addWidget(self.button_box)
        self.setLayout(self.main_layout)

        self.button_box.accepted.connect(self.on_export_button_clicked)
        self.button_box.rejected.connect(self.reject)
        self.export_dir_button.clicked.connect(self.on_export_dir_button_clicked)
        self.export_dir_line.editingFinished.connect(self.on_export_dir_line_edited)
        self.file_type_box.currentIndexChanged.connect(self.on_override_param_changed)
        self.texture_res_box.currentIndexChanged.connect(self.on_override_param_changed)

        self.dialog_vars = {}
        self.export_config = copy.deepcopy(export_config)

        painter_ev.DISPATCHER.connect(
            painter_ev.ExportTexturesEnded,
            self.on_export_textures_ended
        )
        self.accepted.connect(self.on_dialog_accepted)

    @Slot()
    def on_export_button_clicked(self):
        self.export_project()

    def enable_buttons(self, **kwargs):
        export_dir = kwargs.setdefault("export_dir", self.dialog_vars["export_dir"])
        p = Path(export_dir)
        if export_dir and p.exists():
            self.export_dir_line.setText(export_dir)
            self.set_dialog_vars()
            self.set_exports()
            self.show_exports()
            self.export_button.setEnabled(True)
            self.export_button.setDefault(True)
            self.cancel_button.setDefault(False)

    def set_exports(self):
        self.export_config["exportList"] = [{
            "rootPath": painter_tex.get_active_stack().material().name(),
            "exportPreset": "Shapeshift"
        }]
        self.export_config["exportPath"] = self.dialog_vars["export_dir"]
        self.export_config["exportParameters"][0]["parameters"]["fileFormat"] = str(
            self.dialog_vars["file_type"]
        )
        self.export_config["exportParameters"][0]["parameters"]["sizelog2"] = int(
            math.log2(self.dialog_vars["texture_res"])
        )

    def show_exports(self):
        # exports = painter_exp.list_project_textures(self.export_config)
        # exports_text = "\n".join(next(iter(exports.values())))
        # self.export_list_box.setPlainText(exports_text)

        dict_ = painter_exp.list_project_textures(self.export_config)
        items = []
        for k, vs in dict_.items():
            item = QTreeWidgetItem([self.dialog_vars["export_dir"]])
            for v in vs:
                p = Path(v)
                child = QTreeWidgetItem([p.name, str(self.dialog_vars["texture_res"])])
                item.addChild(child)
            items.append(item)
        self.export_tree.insertTopLevelItems(0, items)
        self.export_tree.expandItem(next(iter(items)))

    @Slot()
    def on_export_dir_line_edited(self):
        self.enable_buttons(export_dir=self.export_dir_line.text())

    @Slot()
    def on_export_dir_button_clicked(self):
        export_dir = QFileDialog.getExistingDirectory(
            parent=self,
            caption="Open Export Directory",
            dir=self.export_dir_start_path,
            options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        self.enable_buttons(export_dir=export_dir)

    @Slot()
    def on_override_param_changed(self):
        self.enable_buttons()

    @Slot()
    def on_dialog_ready_for_accept(self):
        time.sleep(3)
        self.accept()

    @Slot()
    def on_dialog_accepted(self):
        self.logbox.widget.clear()
        p = Path(self.export_dir_line.text())
        self.export_dir_start_path = str(p.parent)

    def get_textureset_res(self):
        res = painter_tex.get_active_stack().material().get_resolution()
        if res.height != res.width:
            try:
                raise ValueError(
                    f"Invalid 1:1 Texture Ratio: {res.height} x {res.width}"
                )
            except ValueError as e:
                painter_log.log(
                    painter_log.ERROR,
                    "shapeshift",
                    f"Texture Resolution Error: {e}"
                )
                raise
        return res.height

    def set_dialog_vars(self):
        self.dialog_vars["export_dir"] = self.export_dir_line.text()
        self.dialog_vars["file_type"] = self.file_type_box.currentText()

        texture_res = self.texture_res_box.currentText()
        if texture_res == "Current":
            texture_res = self.get_textureset_res()

        try:
            texture_res = int(texture_res)
        except ValueError as e:
            painter_log.log(
                painter_log.ERROR,
                "shapeshift",
                f"Texture Resolution Error: {e}"
            )
            raise
        else:
            self.dialog_vars["texture_res"] = texture_res

        painter_log.log(
            painter_log.DBG_INFO,
            "shapeshift",
            pprint.saferepr(self.dialog_vars)
        )

    def export_project(self):
        self.logger.info("Export Project...")
        try:
            painter_exp.export_project_textures(self.export_config)
        except (painter_exc.ProjectError, ValueError) as e:
            painter_log.log(
                painter_log.ERROR,
                "shapeshift",
                f"Project Export Error: {e}"
            )
            raise

    @Slot()
    def on_export_textures_ended(self, ev):
        self.logger.info(ev.str)
        if ev.status in ["Cancelled"]:
            self.logger.info("Export Project Cancelled")
            self.logger.info(ev.str)
        elif ev.status in ["Warning"]:
            self.logger.info("Export Project Warning")
            self.logger.warning(ev.str)
        elif ev.status in ["Error"]:
            self.logger.info("Export Project Error")
            self.logger.error(ev.str)
        elif ev.status == "Success":
            exports_text = "\n".join(ev.textures.values())
            self.logger.info(exports_text)
            self.logger.info("Export Project Success")
            self.logger.info("Export Project Done.")
            self.on_dialog_ready_for_accept()


class CreateDialog(QDialog):

    def __init__(self):
        super(CreateDialog, self).__init__(parent=painter_ui.get_main_window())
        self.init_UI()

    def init_UI(self):
        self.create_action = QWidgetAction(self)
        self.create_action.setText("Create UE Project...")
        self.create_action.triggered.connect(self.exec_)

        self.setWindowTitle("Create UE Project")

        self.create_button = QPushButton("Create", parent=self)
        self.create_button.setEnabled(False)
        self.create_button.setDefault(False)
        self.cancel_button = QPushButton("Cancel", parent=self)
        self.cancel_button.setEnabled(True)
        self.cancel_button.setDefault(True)
        self.button_box = QDialogButtonBox(parent=self)
        self.button_box.addButton(self.create_button, QDialogButtonBox.AcceptRole)
        self.button_box.addButton(self.cancel_button, QDialogButtonBox.RejectRole)

        self.main_layout = QVBoxLayout(self)

        self.mesh_file_layout = QHBoxLayout(self)
        self.mesh_file_label = QLabel(parent=self)
        self.mesh_file_label.setText("Mesh File")
        self.mesh_file_label.setAlignment(Qt.AlignLeft)
        self.mesh_file_line = QLineEdit(parent=self)
        self.mesh_file_button = QToolButton(parent=self)
        # self.mesh_file_button.setIcon(QIcon("SP_DialogOpenButton"))
        self.mesh_file_label.setBuddy(self.mesh_file_line)
        self.mesh_file_start_path = str(Path.home())

        self.mesh_file_layout.addWidget(self.mesh_file_line)
        self.mesh_file_layout.addWidget(self.mesh_file_button)

        self.mesh_map_layout = QHBoxLayout(self)
        self.bake_checkbox = QCheckBox("Bake Mesh Maps", parent=self)
        self.bake_checkbox.setCheckState(Qt.Checked)
        self.mesh_map_spacer = QSpacerItem(60, 0)
        self.texture_res_box = QComboBox(parent=self)
        self.texture_res_box.addItems([
            "256",
            "512",
            "1024",
            "2048",
            "4096",
            "8192",
        ])
        self.texture_res_box.setCurrentIndex(3)
        self.texture_res_label = QLabel(parent=self)
        self.texture_res_label.setText("Texture Resolution")
        self.texture_res_label.setBuddy(self.texture_res_box)

        self.mesh_map_layout.addWidget(self.bake_checkbox)
        self.mesh_map_layout.addSpacerItem(self.mesh_map_spacer)
        self.mesh_map_layout.addWidget(self.texture_res_label)
        self.mesh_map_layout.addWidget(self.texture_res_box)

        self.logbox = QPlainTextEditLogger(self)
        self.logbox_label = QLabel(parent=self)
        self.logbox_label.setText("Logs")
        self.logbox_label.setBuddy(self.logbox.widget)

        self.logbox_handler = QLogHandler(self.logbox)
        self.logger = logging.getLogger()
        self.logger.addHandler(self.logbox_handler)
        self.logger.setLevel(logging.DEBUG)

        self.main_layout.addWidget(self.mesh_file_label)
        self.main_layout.addLayout(self.mesh_file_layout)
        self.main_layout.addLayout(self.mesh_map_layout)
        self.main_layout.addWidget(self.logbox_label)
        self.main_layout.addWidget(self.logbox.widget)
        self.main_layout.addWidget(self.button_box)
        self.setLayout(self.main_layout)

        self.button_box.accepted.connect(self.on_create_button_clicked)
        self.button_box.rejected.connect(self.reject)
        self.mesh_file_button.clicked.connect(self.on_mesh_file_button_clicked)
        self.mesh_file_line.editingFinished.connect(self.on_mesh_file_line_edited)
        self.bake_checkbox.stateChanged.connect(self.on_bake_checkbox_changed)

        self.dialog_vars = {}

        painter_ev.DISPATCHER.connect(
            painter_ev.ProjectCreated,
            self.on_project_created
        )

        painter_ev.DISPATCHER.connect(
            painter_ev.ProjectEditionEntered,
            self.on_project_edition_entered
        )

        self.accepted.connect(self.on_dialog_accepted)

    @Slot()
    def on_create_button_clicked(self):
        self.set_dialog_vars()
        self.create_project()

    @Slot()
    def on_project_created(self, ev):
        self.logger.info("Create Project Done.")

    @Slot()
    def on_project_edition_entered(self, ev):
        self.bake_maps()

    def enable_buttons(self, mesh_file_path):
        p = Path(mesh_file_path)
        if mesh_file_path and p.exists():
            self.mesh_file_line.setText(mesh_file_path)
            self.create_button.setEnabled(True)
            self.create_button.setDefault(True)
            self.cancel_button.setDefault(False)

    @Slot()
    def on_mesh_file_line_edited(self):
        self.enable_buttons(self.mesh_file_line.text())

    @Slot()
    def on_mesh_file_button_clicked(self):
        mesh_file_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption="Open Static Mesh",
            dir=self.mesh_file_start_path,
            filter="Static Mesh Files (*.fbx)"
        )
        self.enable_buttons(mesh_file_path)

    @Slot()
    def on_bake_checkbox_changed(self):
        if self.bake_checkbox.isChecked():
            self.texture_res_box.setEnabled(True)
        else:
            self.texture_res_box.setEnabled(False)

    @Slot()
    def on_dialog_ready_for_accept(self):
        time.sleep(3)
        self.accept()

    @Slot()
    def on_dialog_accepted(self):
        self.logbox.widget.clear()
        p = Path(self.mesh_file_line.text())
        self.mesh_file_start_path = str(p.parent)

    @Slot()
    def on_baker_result(self, mesh_maps):
        self.import_maps(mesh_maps)

    def set_dialog_vars(self):
        self.dialog_vars["mesh_file_path"] = self.mesh_file_line.text()

        if self.bake_checkbox.checkState() == Qt.CheckState.Checked:
            self.dialog_vars["is_bake_maps_checked"] = True
        elif self.bake_checkbox.checkState() == Qt.CheckState.Unchecked:
            self.dialog_vars["is_bake_maps_checked"] = False

        try:
            texture_res = int(self.texture_res_box.currentText())
        except ValueError as e:
            painter_log.log(
                painter_log.ERROR,
                "shapeshift",
                f"Texture Resolution Error: {e}"
            )
            raise
        else:
            self.dialog_vars["texture_res"] = texture_res

        painter_log.log(
            painter_log.DBG_INFO,
            "shapeshift",
            pprint.saferepr(self.dialog_vars)
        )

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

    def create_project(self):
        project_settings = self.get_project_settings(
            self.dialog_vars["mesh_file_path"],
            self.dialog_vars["texture_res"]
        )
        if painter_proj.is_open():
            painter_log.log(
                painter_log.ERROR,
                "shapeshift",
                f"Project Already Open Error: {painter_proj.name()}"
            )
        else:
            self.logger.info("Create Project...")
            try:
                painter_proj.create(
                    self.dialog_vars["mesh_file_path"],
                    # template_file_path=
                    settings=project_settings
                )
            except (painter_exc.ProjectError, ValueError) as e:
                painter_log.log(
                    painter_log.ERROR,
                    "shapeshift",
                    f"Project Creation Error: {e}"
                )
                raise

    def bake_maps(self):
        if self.dialog_vars["is_bake_maps_checked"]:
            self.logbox_handler = QLogHandler(self.logbox)
            self.baker_thread = QThread(parent=None)
            self.baker = Baker(
                self.dialog_vars["mesh_file_path"],
                self.dialog_vars["texture_res"],
                extra_handler=self.logbox_handler
            )
            self.baker.moveToThread(self.baker_thread)
            self.baker_thread.started.connect(self.baker.run)
            self.baker.result.connect(self.on_baker_result)
            self.baker.finished.connect(self.baker_thread.quit)
            self.baker.finished.connect(self.baker.deleteLater)
            self.baker_thread.finished.connect(self.baker_thread.deleteLater)

            self.baker_thread.start()
            self.baker_thread.setPriority(QThread.LowestPriority)
        else:
            self.on_dialog_ready_for_accept()

    def import_maps(self, mesh_maps):
        self.importer_thread = QThread(parent=None)
        self.importer = Importer(
            self.dialog_vars["mesh_file_path"],
            mesh_maps,
            extra_handler=self.logbox_handler
        )
        self.importer.moveToThread(self.importer_thread)
        self.importer_thread.started.connect(self.importer.run)
        self.importer.finished.connect(self.importer_thread.quit)
        self.importer_thread.finished.connect(self.on_dialog_ready_for_accept)
        self.importer.finished.connect(self.importer.deleteLater)
        self.importer_thread.finished.connect(self.importer_thread.deleteLater)
        self.importer_thread.start()
        self.importer_thread.setPriority(QThread.LowestPriority)


def start_plugin():
    app_menu = QMenu(parent=painter_ui.get_main_window())
    app_menu.setTitle("Shapeshift")
    create_dialog = CreateDialog()
    export_dialog = ExportDialog()
    app_menu.addAction(create_dialog.create_action)
    app_menu.addAction(export_dialog.export_action)
    painter_ui.add_menu(
        app_menu
    )
    plugin_widgets.append(app_menu)
    return None


def close_plugin():
    for widget in plugin_widgets:
        painter_ui.delete_ui_element(widget)

    plugin_widgets.clear()
    return None


def reload_plugin():
    deps = [
        baketools,
        importtools
    ]
    for dep in deps:
        importlib.reload(dep)

    return None


if __name__ == "__main__":
    start_plugin()
