#!usr/bin/env python3

import logging
import os
import pkg_resources
import sys

logging.basicConfig(level=logging.INFO)


def main():
    painter_plugin_path = "SUBSTANCE_PAINTER_PLUGINS_PATH"
    shapeshift_pkg = pkg_resources.get_distribution("shapeshift")
    shapeshift_plugin_path = (
        f"{shapeshift_pkg.location}/"
        "shapeshift/substance_painter"
    )
    if os.path.exists(shapeshift_plugin_path):
        print(
            "Add to your environment and restart Substance 3D Painter."
            f"{painter_plugin_path}={shapeshift_plugin_path}"
        )
    return None


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Exceptions Detected, Exiting.")
        sys.exit(1)
