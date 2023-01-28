#!/usr/bin/env python3

import os.path
from pathlib import Path

import substance_painter.exception as painter_exc
import substance_painter.logging as painter_log
import substance_painter.ui as painter_ui
import substance_painter.project as painter_proj

from PySide2 import QtWidgets
from shapeshift.constants import _const as CONSTANTS

plugin_widgets = []


def get_project_settings(mesh_file_path, texture_res):
    texture_dir_path = os.path.dirname(mesh_file_path).replace(
        "Meshes",
        "Textures"
    )
    project_settings = painter_proj.Settings(
        default_texture_resolution=texture_res,
        export_path=texture_dir_path,
        import_cameras=False,
        normal_map_format=painter_proj.NormalMapFormat.DirectX,
        tangent_space_mode=painter_proj.TangentSpace.PerFragment
    )
    return project_settings


def create_project(mesh_file_path, texture_res):
    try:
        painter_proj.create(
            mesh_file_path=mesh_file_path,
            # template_file_path=
            settings=get_project_settings(
                mesh_file_path,
                texture_res
            )
        )
    except (painter_exc.ProjectError, ValueError) as e:
        painter_log.log(
            painter_log.ERROR,
            "shapeshift",
            f"Project Creation Error: {e}"
        )
    return None


def get_mesh_file_path():
    mesh_file_path = QtWidgets.QFileDialog.getOpenFileName(
        self,
        "Open Static Mesh",
        Path.home(),
        "Static Mesh Files (*.fbx)"
    )
    with mesh_file_path:
        create_project(
            mesh_file_path,
            CONSTANTS().TEXTURE_RES
        )
    return None


def start_plugin():
    BuildUEAction = QtWidgets.QAction(
        "Build UE Project",
        triggered=get_mesh_file_path
    )
    shapeshiftMenu = QtWidgets.QMenu("Shapeshift", parent=None)
    # shapeshiftMenu.addAction(BuildUEAction)
    painter_ui.add_action(
        menu=shapeshiftMenu,
        action=BuildUEAction,
    )
    painter_ui.add_menu(
        shapeshiftMenu
    )
    plugin_widgets.append(shapeshiftMenu)
    return None


def close_plugin():
    for widget in plugin_widgets:
        painter_ui.delete_ui_element(widget)

    plugin_widgets.clear()
    return None


if __name__ == "__main__":
    start_plugin()
