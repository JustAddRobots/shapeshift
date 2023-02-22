#!/usr/bin/env python3

import datetime
import math
import os
import platform
import pprint
import re
import tempfile
from pathlib import Path

import substance_painter.logging as painter_log

from shapeshift.common import command


class MeshMap():

    def __init__(self, mesh_file_path, texture_res):
        self._mesh_file_path = self._get_mesh_file_path(mesh_file_path)
        self._texture_res = self._get_texture_res(texture_res)
        self._sbsbaker_path = self._get_sbsbaker_path()

    @property
    def mesh_file_path(self):
        return self._mesh_file_path

    @property
    def texture_res(self):
        return self._texture_res

    @property
    def baked_mesh_maps(self):
        return self._baked_mesh_maps

    def get_baked_mesh_maps(self):
        return self._get_baked_mesh_maps()

    def get_baked_mesh_maps_mp(self):
        return self._get_baked_mesh_maps_mp()

    def _get_mesh_file_path(self, path):
        mesh_file_path = ""
        p = Path(path)
        if path and p.exists():
            mesh_file_path = path
        else:
            try:
                raise ValueError(f"Invalid mesh_file_path: {path}")
            except ValueError as e:
                painter_log.log(
                    painter_log.ERROR,
                    "shapeshift",
                    f"Bake Error: {e}"
                )
                raise
        return mesh_file_path

    def _get_texture_res(self, res):
        texture_res = None
        try:
            int(res)
        except ValueError as e:
            painter_log.log(
                painter_log.ERROR,
                "shapeshift",
                f"Bake Error: {e}"
            )
            raise
        else:
            if (math.log2(res).is_integer() and res >= 32 and res <= 8192):
                texture_res = res
            else:
                try:
                    raise ValueError(f"Invalid texture_res: {res}")
                except ValueError as e:
                    painter_log.log(
                        painter_log.ERROR,
                        "shapeshift",
                        f"Bake Error: {e}"
                    )
                    raise
        return texture_res

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
        p = Path(substance_designer_path)
        if substance_designer_path and p.exists():
            painter_log.log(
                painter_log.DBG_INFO,
                "shapeshift",
                f"substance_designer_path: {substance_designer_path}"
            )
        else:
            try:
                raise ValueError(
                    f"Invalid substance_designer_path: {substance_designer_path}"
                )
            except ValueError as e:
                painter_log.log(
                    painter_log.ERROR,
                    "shapeshift",
                    f"Bake Error: {e}"
                )
                raise
        return substance_designer_path

    def _get_sbsbaker_path(self):
        sbsbaker_path = ""
        substance_designer_path = self._get_substance_designer_path()
        if substance_designer_path:
            for path, directory, files in os.walk(substance_designer_path):
                if "sbsbaker" in files:
                    sbsbaker_path = f"{path}/sbsbaker"
                    break
        p = Path(sbsbaker_path)
        if sbsbaker_path and p.exists():
            painter_log.log(
                painter_log.DBG_INFO,
                "shapeshift",
                f"sbsbaker_path: {sbsbaker_path}"
            )
        else:
            try:
                raise ValueError(
                    f"Invalid sbsbaker_path: {sbsbaker_path}"
                )
            except ValueError as e:
                painter_log.log(
                    painter_log.ERROR,
                    "shapeshift",
                    f"Bake Error: {e}"
                )
                raise
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

    def _bake_map(self, mesh_map, tmp_bake_dir, texture_res):
        result = None
        size = int(math.log2(texture_res))
        cmd = [
            f"--inputs {self._mesh_file_path}",
            f"--output-path {tmp_bake_dir}",
            f"--output-name {{inputName}}.{mesh_map}",
            "--output-format tga",
            f"--output-size {size},{size}",
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
        baked_mesh_maps = {}
        maps_to_bake = (
            "normal",
            "normal-world-space",
            "ambient-occlusion",
            "curvature",
            "position",
        )
        tmp_bake_dir = self._get_tmp_bake_dir()
        painter_log.log(painter_log.INFO, "shapeshift", "Bake Mesh Maps...")
        for mesh_map in maps_to_bake:
            painter_log.log(
                painter_log.DBG_INFO,
                "shapeshift",
                f"Baking Map: {mesh_map}"
            )
            painter_log.log(
                painter_log.INFO,
                "shapeshift",
                f"Baking Map: {mesh_map}"
            )
            try:
                result = self._bake_map(
                    mesh_map,
                    tmp_bake_dir,
                    self._texture_res
                )
            except (OSError, ValueError) as e:
                painter_log.log(
                    painter_log.ERROR,
                    "shapeshift",
                    f"Bake Error, {mesh_map}: {e}"
                )
                raise
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
                                match[2],  # msg
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
        return baked_mesh_maps

    def _put_status(self, queue, **kwargs):
        msg = kwargs
        queue.put(msg)
        return None

    def _get_baked_mesh_maps_mp(self, mpq):
        baked_mesh_maps = {}
        maps_to_bake = (
            "normal",
            "normal-world-space",
            "ambient-occlusion",
            "curvature",
            "position",
        )
        tmp_bake_dir = self._get_tmp_bake_dir()
        painter_log.log(painter_log.INFO, "shapeshift", "Bake Mesh Maps...")
        for mesh_map in maps_to_bake:
            painter_log.log(
                painter_log.DBG_INFO,
                "shapeshift",
                f"Baking Map: {mesh_map}"
            )
            painter_log.log(
                painter_log.INFO,
                "shapeshift",
                f"Baking Map: {mesh_map}"
            )
            self._put_status(
                mpq,
                status="PENDING",
                log=f"Baking Map: {mesh_map}"
            )
            try:
                result = self._bake_map(
                    mesh_map,
                    tmp_bake_dir,
                    self._texture_res
                )
            except (OSError, ValueError) as e:
                painter_log.log(
                    painter_log.ERROR,
                    "shapeshift",
                    f"Bake Error, {mesh_map}: {e}"
                )
                raise
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
                                match[2],  # msg
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
        self._put_status(
            mpq,
            status="COMPLETED",
            maps=baked_mesh_maps
        )
        return baked_mesh_maps


# texset = tex.TextureSet.from_name("M_Structure_Office_Wall_A")
# mmrsc = texset.get_mesh_map_resource(tex.MeshMapUsage.AO)
