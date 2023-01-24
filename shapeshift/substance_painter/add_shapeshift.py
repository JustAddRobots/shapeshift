#!usr/bin/env python3

import logging
import os
import pkg_resources
import sys


def main():
    painter_plugin_path = "SUBSTANCE_PAINTER_PLUGINS_PATH"
    shapeshift_pkg = pkg_resources.get_distribution("shapeshift")
    shapeshift_plugin_path = (
        f"{shapeshift_pkg.location}/"
        "shapeshift/substance_painter"
    )
    if painter_plugin_path in os.environ.keys():
        if shapeshift_plugin_path in os.environ[painter_plugin_path]:
            logging.info("Found shapeshift plugin path in environment.")
        else:
            logging.info("Adding shapeshift plugin path to environment.")
            os.environ[painter_plugin_path].append(shapeshift_plugin_path)
    else:
        logging.info("Adding shapeshift plugin path to environment.")
        os.environ[painter_plugin_path] = shapeshift_plugin_path
    return None


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Exceptions Detected, Exiting.")
        sys.exit(1)
