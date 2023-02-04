#!/usr/bin/env python3

import os.path
from pathlib import Path

from PySide2 import QtWidgets
import substance_painter.exception as painter_exc
import substance_painter.logging as painter_log
import substance_painter.ui as painter_ui
import substance_painter.project as painter_proj

from shapeshift.substance3d.modules import baketools
from shapeshift.common.constants import _const as CONSTANTS

plugin_widgets = []


class ShapeshiftMenu(QtWidgets.QMenu):

    def __init__(self):
        super(ShapeshiftMenu, self).__init__("Shapeshift", parent=None)
        self._mesh_file_path = ""

        create_ue = QtWidgets.QWidgetAction(self)
        create_ue.setText("Create UE Project")
        create_ue.triggered.connect(self._create_project)
        self.addAction(_create_ue)

        mesh_map = baketools.MeshMap(self._mesh_file_path)
        bake_maps = QtWidgets.QWidgetAction(self)
        bake_maps.setText("Bake Mesh Maps")
        bake_maps.triggered.connect(mesh_map.bake_mesh_maps)
        self.addAction(bake_maps)

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
        return None

    def _get_mesh_file_path(self):
        mesh_file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
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
