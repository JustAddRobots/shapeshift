import logging
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
# from PySide2.QtGui import QIcon

import substance_painter.event as painter_ev
import substance_painter.exception as painter_exc
import substance_painter.logging as painter_log
import substance_painter.project as painter_proj
import substance_painter.ui as painter_ui

from shapeshift.substance3d.modules import baketools
from shapeshift.substance3d.modules import importtools
from shapeshift.substance3d.modules.logbox import QLogHandler
from shapeshift.substance3d.modules.logbox import QPlainTextEditLogger

plugin_widgets = []


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
            self.cancel_button.setEnabled(True)
            self.cancel_button.setDefault(False)
        else:
            self.create_button.setEnabled(False)
            self.create_button.setDefault(False)
            self.cancel_button.setEnabled(True)
            self.cancel_button.setDefault(True)

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
