#!/usr/bin/env python3

import datetime
import os.walk
import platform
import tempfile

# import substance_painter.exception as painter_exc
import substance_painter.logging as painter_log

from shapeshift.common import command
# from shapeshift.common.constants import _const as CONSTANTS


class MeshMap():

    def __init__(self, mesh_file_path):
        self._mesh_file_path = mesh_file_path
        self._sbsbaker_path = self._get_sbsbaker_path()

    def _get_substance_designer_path(self):
        substance_designer_path = ""
        if platform.system() == "Darwin":
            cmd = (
                """mdfind "kMDItemKind == 'Application'" | """
                """grep "Adobe Substance 3D Designer" | """
                """grep ^/Applications"""
            )
        substance_designer_path = command.get_shell_cmd(cmd)["stdout"]
        return substance_designer_path

    def _get_sbsbaker_path(self):
        sbsbaker_path = ""
        substance_designer_path = self._get_substance_designer_path()
        if substance_designer_path:
            for path, directory, files in os.walk(substance_designer_path):
                if "sbsbaker" in files:
                    sbsbaker_path = path
                    break
        return sbsbaker_path

    def _get_tmp_bake_dir(self):
        tmpdir = tempfile.gettempdir()
        tmp_bake_dir = (
            f"{tmpdir}/shapeshift-{datetime.datetime.now().isoformat()}"
        )
        return tmp_bake_dir

    def _bake_map(self, mesh_map, tmp_bake_dir):
        result = None
        cmd = [
            f"--inputs {self._mesh_file_path}",
            f"--output-path {tmp_bake_dir}",
            f"--output-name {{inputName}}.{mesh_map}",
            "--output-format tga",
            "--output-size 11,11",
        ]
        if mesh_map == "normal-world-space":
            cmd.insert(0, f"{self._sbsbaker_path} {mesh_map}")
        else:
            cmd.insert(0, f"{self._sbsbaker_path} {mesh_map}-from-mesh")
            cmd.extend(
                "--antialiasing 2",
                "--use-lowdef-as-highdef true"
            )
        cmd = " ".join(cmd)
        result = command.get_shell_command(cmd)
        return result

    def _bake_mesh_maps(self):
        if os.path.exists(self._mesh_file_path) and self._sbsbaker_path:
            tmp_bake_dir = self._get_tmp_bake_dir()
            mesh_maps = [
                "normal",
                "normal-world-space",
                "ambient-occlusion",
                "curvature",
                "position",
            ]
            for mesh_map in mesh_maps:
                try:
                    self._bake_map(mesh_map, tmp_bake_dir)
                except (OSError, ValueError) as e:
                    painter_log.log(
                        painter_log.ERROR,
                        "shapeshift",
                        f"Bake Error, {mesh_map}: {e}"
                    )
                    # QT Alert
        else:
            pass
            # QT alert
        return None

    def bake_mesh_maps(self):
        self._bake_mesh_maps()


# texset = tex.TextureSet.from_name("M_Structure_Office_Wall_A")
# mmrsc = texset.get_mesh_map_resource(tex.MeshMapUsage.AO)
