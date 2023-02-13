#!usr/bin/env python3

import logging
import os
import pkg_resources
import sys

logging.basicConfig(level=logging.INFO)


def main():
    envar_painter_plugin_path = "SUBSTANCE_PAINTER_PLUGINS_PATH"
    envar_pythonpath = "PYTHONPATH"
    shapeshift_pkg = pkg_resources.get_distribution("shapeshift")
    shapeshift_location = f"{shapeshift_pkg.location}"
    shapeshift_plugin_path = (
        f"{shapeshift_location}/"
        "shapeshift/substance3d"
    )
    if os.path.exists(shapeshift_plugin_path):
        print(
            "Add to your environment and restart Substance 3D Painter.\n"
            f"{envar_pythonpath}={shapeshift_location}\n"
            f"{envar_painter_plugin_path}={shapeshift_plugin_path}\n"
        )
    return None


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Exceptions Detected, Exiting.")
        sys.exit(1)
