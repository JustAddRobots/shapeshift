import os
from setuptools import setup


def readme():
    with open("README.md") as f:
        return f.read()


with open(os.path.dirname(__file__) + "/VERSION") as f:
    pkgversion = f.read().strip()


setup(
    name="shapeshift",
    version=pkgversion,
    description="Tools for 3D Pipelines",
    url="https://github.com/JustAddRobots/shapeshift",
    author="Roderick Constance",
    author_email="justaddrobots@icloud.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
    ],
    license="GPLv3",
    python_requires=">=3.6",
    packages=[
        "shapeshift",
        "shapeshift.blender",
        "shapeshift.common",
        "shapeshift.substance3d",
        "shapeshift.substance3d.modules",
        "shapeshift.substance3d.plugins",
        "shapeshift.substance3d.startup",

    ],
    entry_points={
        "console_scripts": [
            "add_shapeshift=shapeshift.substance3d.add_shapeshift:main"
        ]
    },
    zip_safe = False
)
