#!/usr/bin/env python3

import datetime
import os
import platform
import pprint
import re
import tempfile
from pathlib import Path

# import substance_painter.exception as painter_exc
import substance_painter.logging as painter_log

from shapeshift.common import command
# from shapeshift.common.constants import _const as CONSTANTS


class MeshMap():

    def __init__(self, mesh_file_path):
        self._mesh_file_path = mesh_file_path
        self._sbsbaker_path = self._get_sbsbaker_path()
        # self._baked_mesh_maps = self._get_baked_mesh_maps()

    @property
    def baked_mesh_maps(self):
        return self._baked_mesh_maps

    def _get_substance_designer_path(self):
        substance_designer_path = ""
        if platform.system() == "Darwin":
            cmd = (
                """mdfind "kMDItemKind == 'Application'" | """
                """grep "Adobe Substance 3D Designer" | """
                """grep ^/Applications"""
            )
        substance_designer_path = command.get_shell_cmd(cmd)["stdout"]
        substance_designer_path = substance_designer_path.strip()
        painter_log.log(
            painter_log.DBG_INFO,
            "shapeshift",
            f"substance_designer_path: {substance_designer_path}"
        )
        return substance_designer_path

    def _get_sbsbaker_path(self):
        sbsbaker_path = ""
        substance_designer_path = self._get_substance_designer_path()
        if substance_designer_path:
            for path, directory, files in os.walk(substance_designer_path):
                if "sbsbaker" in files:
                    sbsbaker_path = f"{path}/sbsbaker"
                    break
        painter_log.log(
            painter_log.DBG_INFO,
            "shapeshift",
            f"sbsbaker_path: {sbsbaker_path}"
        )
        return sbsbaker_path

    def _get_tmp_bake_dir(self):
        tmpdir = tempfile.gettempdir()
        tmp_bake_dir = (
            f"{tmpdir}/shapeshift-{datetime.datetime.now().isoformat()}"
        )
        painter_log.log(
            painter_log.DBG_INFO,
            "shapeshift",
            f"tmp_bake_dir: {tmp_bake_dir}"
        )
        os.makedirs(tmp_bake_dir)
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
            cmd.insert(0, f"{re.escape(self._sbsbaker_path)} {mesh_map}")
        else:
            cmd.insert(0, f"{re.escape(self._sbsbaker_path)} {mesh_map}-from-mesh")
            cmd.extend([
                "--antialiasing 2",
                "--use-lowdef-as-highdef true"
            ])
        cmd = " ".join(cmd)
        painter_log.log(painter_log.DBG_INFO, "shapeshift", f"cmd: {cmd}")
        result = command.get_shell_cmd(cmd)
        return result

    def _get_baked_mesh_maps(self):
        if os.path.exists(self._mesh_file_path) and self._sbsbaker_path:
            baked_mesh_maps = {}
            maps_to_bake = (
                "normal",
                "normal-world-space",
                "ambient-occlusion",
                "curvature",
                "position",
            )
            tmp_bake_dir = self._get_tmp_bake_dir()
            painter_log.log(painter_log.INFO, "shapeshift", "Baking Mesh Maps...")
            for mesh_map in maps_to_bake:
                painter_log.log(
                    painter_log.DBG_INFO,
                    "shapeshift",
                    f"Baking Map: {mesh_map}"
                )
                try:
                    result = self._bake_map(mesh_map, tmp_bake_dir)
                except (OSError, ValueError) as e:
                    painter_log.log(
                        painter_log.ERROR,
                        "shapeshift",
                        f"Bake Error, {mesh_map}: {e}"
                    )
                    # QT Alert
                else:
                    # Capture stderr from command-line bake tool.
                    if result["stderr"]:
                        regex = r"\[ERROR\]\[(.*)\](.*)"
                        for line in result["stderr"].split("/n"):
                            match = re.search(regex, line)
                            if match:
                                painter_log.log(
                                    painter_log.ERROR,
                                    match[1],  # channel
                                    match[2],
                                )
                    else:
                        mesh_map_file = (
                            f"{tmp_bake_dir}/"
                            f"{Path(self._mesh_file_path).stem}.{mesh_map}.tga"
                        )
                        baked_mesh_maps[mesh_map] = mesh_map_file
            painter_log.log(painter_log.INFO, "shapeshift", "Bake Mesh Maps Done.")
            painter_log.log(
                painter_log.DBG_INFO,
                "shapeshift",
                pprint.saferepr(baked_mesh_maps)
            )
        else:
            pass
            # QT alert
        return baked_mesh_maps

    def get_baked_mesh_maps(self):
        self._get_baked_mesh_maps()


# texset = tex.TextureSet.from_name("M_Structure_Office_Wall_A")
# mmrsc = texset.get_mesh_map_resource(tex.MeshMapUsage.AO)
