from zipfile import ZipFile
from gamuLogger import debug, Logger
import os

Logger.setModule("createModule")

def addFolderToZip(zip: ZipFile, arc_path, folder, parent_folder = ""):
    debug(f"Adding folder {folder} to zip")
    for file in os.listdir(folder):
        file_path = os.path.join(folder, file)
        if os.path.isfile(file_path):
            debug(f"Adding file {file} to zip")
            zip.write(file_path, os.path.join(arc_path, parent_folder, file))
        elif os.path.isdir(file_path):
            addFolderToZip(zip, arc_path, file_path, os.path.join(parent_folder, file))