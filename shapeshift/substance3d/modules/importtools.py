#!/usr/bin/env python3

import copy
import logging
from pathlib import Path

import substance_painter.exception as painter_exc
import substance_painter.logging as painter_log
import substance_painter.project as painter_proj
import substance_painter.resource as painter_rsc
import substance_painter.textureset as painter_tex


class TexSet():

    def __init__(self, mesh_file_path, mesh_maps, **kwargs):
        self._mesh_file_path = self._get_mesh_file_path(mesh_file_path)
        self._mesh_maps = self._get_mesh_maps(mesh_maps)
        self._logger = logging.getLogger()
        self._extra_handler = kwargs.setdefault("extra_handler", None)
        if self._extra_handler:
            self._logger.addHandler(self._extra_handler)

    def import_mesh_maps(self):
        return self._import_mesh_maps()

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

    def _get_mesh_maps(self, maps):
        mesh_maps = {}
        if not isinstance(maps, dict):
            try:
                raise ValueError(f"Invalid mesh_maps format: {type(maps)}")
            except ValueError as e:
                painter_log.log(
                    painter_log.ERROR,
                    "shapeshift",
                    f"Import Error: {e}"
                )
                raise
        else:
            valid_map_types = {
                "ambient-occlusion",
                "curvature",
                "normal",
                "normal-world-space",
                "position",
            }
            map_types = set(maps.keys())
            map_diff = map_types.difference(valid_map_types)
            if map_diff:
                try:
                    raise ValueError(f"Invalid mesh_map type: {map_diff}")
                except ValueError as e:
                    painter_log.log(
                        painter_log.ERROR,
                        "shapeshift",
                        f"Import Error: {e}"
                    )
                    raise
            else:
                mesh_maps = copy.deepcopy(maps)
        return mesh_maps

    def _import_mesh_maps(self):
        if not painter_proj.is_in_edition_state():
            painter_log.log(
                painter_log.ERROR,
                "shapeshift",
                "Project Not Ready Error"
            )
            self._logger.error("Project not ready")
        else:
            mesh_stem = Path(self._mesh_file_path).stem
            if mesh_stem.startswith("SM_"):
                material_name = mesh_stem.replace("SM_", "M_", 1)
            else:
                try:
                    raise ValueError(
                        f"Invalid Static Mesh name: {mesh_stem}"
                    )
                except ValueError as e:
                    painter_log.log(
                        painter_log.ERROR,
                        "shapeshift",
                        f"Import Error: {e}"
                    )
                    self._logger.error(f"Import Error: {mesh_map}")
                    raise

            texture_set = painter_tex.TextureSet.from_name(material_name)
            map_usage_LUT = {
                "ambient-occlusion": painter_tex.MeshMapUsage.AO,
                "curvature": painter_tex.MeshMapUsage.Curvature,
                "normal": painter_tex.MeshMapUsage.Normal,
                "normal-world-space": painter_tex.MeshMapUsage.WorldSpaceNormal,
                "position": painter_tex.MeshMapUsage.Position,
            }
            self._logger.info("Import Baked Maps...")
            for mesh_map, mesh_map_filename in self._mesh_maps.items():
                self._logger.info(f"Importing Map: {mesh_map}")
                try:
                    map_rsc = painter_rsc.import_project_resource(
                        mesh_map_filename,
                        painter_rsc.Usage.TEXTURE
                    )
                except (ValueError, RuntimeError) as e:
                    painter_log.log(
                        painter_log.ERROR,
                        "shapeshift",
                        f"Import Error: {e}"
                    )
                    self._logger.error(f"Import Error: {mesh_map}")
                    raise

                try:
                    texture_set.set_mesh_map_resource(
                        map_usage_LUT[mesh_map],
                        map_rsc.identifier()
                    )
                except (painter_exc.ResourceNotFoundError, ValueError) as e:
                    painter_log.log(
                        painter_log.ERROR,
                        "shapeshift",
                        f"Resource Error: {e}"
                    )
                    self._logger.error(f"Resource Error: {mesh_map}")
                    raise
            self._logger.info("Import Baked Maps Done.")
