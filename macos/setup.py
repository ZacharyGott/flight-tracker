"""Build the macOS Core Location test application with py2app."""

from pathlib import Path
import plistlib

from setuptools import setup


macos_directory = Path(__file__).resolve().parent
project_directory = macos_directory.parent
with (macos_directory / "Info.plist").open("rb") as plist_file:
    info_plist = plistlib.load(plist_file)


setup(
    name="flight-tracker-macos",
    version="0.1.0",
    app=[str(project_directory / "macos_app.py")],
    options={
        "py2app": {
            "plist": info_plist,
            "packages": ["CoreLocation", "Foundation", "objc"],
            "includes": ["PyObjCTools.AppHelper"],
        }
    },
    setup_requires=[
        "py2app>=0.28",
        "pyobjc-framework-Cocoa>=10",
        "pyobjc-framework-CoreLocation>=10",
    ],
)
