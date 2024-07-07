
from zipfile import ZipFile
import json
from datetime import datetime
from .customTypes import Version, ModuleTypes

from gamuLogger import debug

from .utils import addFolderToZip

class Archive:
    def __init__(self, compiled_code_folder, module_name, module_version : Version, module_type : ModuleTypes, module_description, module_author, branch = "main"):
        self.compiled_code_folder = compiled_code_folder
        self.module_name = module_name
        self.module_version = module_version
        self.module_type = module_type
        self.module_description = module_description
        self.module_author = module_author
        self.branch = branch
        
        self.archiveName = f'{self.module_name}-{str(self.module_version)}.gamod'
    
    def create(self):
        self.zipFile = ZipFile(self.archiveName, 'w')
        self.__addCode()
        self.__createJson()
        
    def __addCode(self):
        debug(f"Adding code from {self.compiled_code_folder} to zip")
        addFolderToZip(self.zipFile, "build", self.compiled_code_folder)
    
    def __createJson(self):
        debug(f"Creating json file for module {self.module_name} version {self.module_version}")
        module = {
            "name": self.module_name,
            "version": str(self.module_version),
            "type": str(self.module_type),
            "description": self.module_description,
            "author": self.module_author,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "repository": f"https://github.com/GamuNetwork/{self.module_name}",
            "branch": self.branch
        }
        result = json.dumps(module, indent=4)
        debug(f"Json file created: {result}")
        self.zipFile.writestr('module.json', result)
    
    def __str__(self):
        return self.archiveName
