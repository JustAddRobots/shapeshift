# import copy
import logging
import math
import pprint
from pathlib import Path

from PySide2.QtWidgets import (
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
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidgetAction,
)
from PySide2.QtCore import (
    # QObject,
    Qt,
    # QThread,
    # Signal,
    Slot,
)
# from PySide2.QtGui import QIcon

import substance_painter.export as painter_exp
import substance_painter.logging as painter_log
import substance_painter.textureset as painter_tex
import substance_painter.ui as painter_ui

from shapeshift.substance3d.modules.exportconfig import get_export_config
from shapeshift.substance3d.modules.logbox import QLogHandler
from shapeshift.substance3d.modules.logbox import QPlainTextEditLogger


plugin_widgets = []


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

        self.logbox = QPlainTextEditLogger(self)
        self.logbox_label = QLabel(parent=self)
        self.logbox_label.setText("Logs")
        self.logbox_label.setBuddy(self.logbox.widget)

        self.logbox_handler = QLogHandler(self.logbox)
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(self.logbox_handler)
        self.logger.setLevel(logging.DEBUG)

        self.main_layout.addWidget(self.export_dir_label)
        self.main_layout.addLayout(self.export_dir_layout)
        self.main_layout.addLayout(self.override_param_layout)
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
        self.export_config = get_export_config()

        self.accepted.connect(self.on_dialog_accepted)

    @Slot()
    def on_export_button_clicked(self):
        self.export_result = self.export_textures()
        self.check_export_result()

    def enable_dismiss(self):
        self.export_button.setText("Dismiss")
        self.export_button.setEnabled(True)
        self.export_button.setDefault(True)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setDefault(False)
        self.button_box.accepted.disconnect(self.on_export_button_clicked)
        self.button_box.accepted.connect(self.accept)

    def reset_buttons(self):
        self.export_button.setText("Export")
        self.export_button.setEnabled(False)
        self.export_button.setDefault(False)
        self.cancel_button.setEnabled(True)
        self.cancel_button.setDefault(True)
        self.button_box.accepted.disconnect(self.accept)
        self.button_box.accepted.connect(self.on_export_button_clicked)

    def enable_buttons(self, **kwargs):
        if "export_dir" in self.dialog_vars:
            export_dir = kwargs.setdefault("export_dir", self.dialog_vars["export_dir"])
        else:
            export_dir = kwargs.setdefault("export_dir", "")
        p = Path(export_dir)
        if export_dir and p.exists() and p.is_dir():
            self.export_dir_line.setText(export_dir)
            self.set_dialog_vars()
            self.set_exports()
            self.show_exports()
            self.export_button.setEnabled(True)
            self.export_button.setDefault(True)
            self.cancel_button.setEnabled(True)
            self.cancel_button.setDefault(False)
        else:
            self.export_button.setEnabled(False)
            self.export_button.setDefault(False)
            self.cancel_button.setEnabled(True)
            self.cancel_button.setDefault(True)

    def set_exports(self):
        self.export_config["exportList"] = [{
            "rootPath": painter_tex.get_active_stack().material().name(),
            "exportPreset": "Shapeshift"
        }]
        self.export_config["exportPath"] = self.dialog_vars["export_dir"]
        self.export_config["exportParameters"][0]["parameters"]["fileFormat"] = str(
            self.dialog_vars["file_type"]
        )
        self.export_config["exportParameters"][0]["parameters"]["sizeLog2"] = int(
            math.log2(self.dialog_vars["texture_res"])
        )
        painter_log.log(
            painter_log.DBG_INFO,
            "shapeshift",
            f"export_config: {self.export_config}"
        )

    def show_exports(self):
        self.export_tree.clear()
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
    def on_dialog_accepted(self):
        p = Path(self.export_dir_line.text())
        self.export_dir_start_path = str(p.parent)
        self.reset_buttons()
        self.logbox.widget.clear()
        self.export_tree.clear()

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

    def check_export_result(self):
        painter_log.log(
            painter_log.DBG_INFO,
            "shapeshift",
            f"export_result: {self.export_result.status} "
            f"{self.export_result.textures}"
        )
        if self.export_result.status == painter_exp.ExportStatus.Cancelled:
            self.logger.info("Export Project Cancelled.")
            self.logger.info(self.export_result.message)
        elif self.export_result.status == painter_exp.ExportStatus.Warning:
            self.logger.info("Export Project Warning.")
            self.logger.warning(self.export_result.message)
        elif self.export_result.status == painter_exp.ExportStatus.Error:
            self.logger.info("Export Project Error.")
            self.logger.error(self.export_result.message)
        elif self.export_result.status == painter_exp.ExportStatus.Success:
            exports = "\n".join(next(iter(self.export_result.textures.values())))
            self.logger.info(exports)
            self.logger.info("Export Project Success.")
            self.enable_OK()

    def export_textures(self):
        self.logger.info("Export Project...")
        try:
            export_result = painter_exp.export_project_textures(self.export_config)
        except (painter_exc.ProjectError, ValueError) as e:
            painter_log.log(
                painter_log.ERROR,
                "shapeshift",
                f"Project Export Error: {e}"
            )
            self.logger.error("Export Error: {e}")
            raise
        else:
            return export_result
