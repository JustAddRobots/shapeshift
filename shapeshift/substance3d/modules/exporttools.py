#!/usr/bin/env python3

import logging

import substance_painter.exception as painter_exc
import substance_painter.export as painter_exp
import substance_painter.logging as painter_log

from shapeshift.substance3d.modules.exportconfig import get_export_config


class ExportSet():

    def __init__(self, **kwargs):
        self._export_config = kwargs.setdefault(
            "export_config",
            get_export_config()
        )
        self._extra_handler = kwargs.setdefault("extra_handler", None)
        self._logger = logging.getLogger()
        if self._extra_handler:
            self._logger.addHandler(self._extra_handler)

    def export_textures(self):
        return self._export_textures()

    def _export_textures(self):
        self._logger.info("Export Project...")
        try:
            painter_exp.export_project_textures(self._export_config)
        except (painter_exc.ProjectError, ValueError) as e:
            painter_log.log(
                painter_log.ERROR,
                "shapeshift",
                f"Project Export Error: {e}"
            )
            self._logger.error("Export Error: {e}")
            raise
