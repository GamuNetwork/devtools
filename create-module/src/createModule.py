
from zipfile import ZipFile
import json
from datetime import datetime
import hashlib
import os

from gamuLogger import Logger
from .customTypes import Version, ModuleTypes, Step

from .utils import addFolderToZip

Logger.setModule("createModule")

class Archive:
    def __init__(self,
                 outDir : str,
                 compiled_code_folder : str,
                 module_name : str,
                 module_version : Version,
                 module_type : ModuleTypes,
                 module_description : str,
                 module_author : str,
                 branch : str = "main"):
        self.compiled_code_folder = compiled_code_folder
        self.module_name = module_name
        self.module_version = module_version
        self.module_type = module_type
        self.module_description = module_description
        self.module_author = module_author
        self.branch = branch
        
        self.archiveName = f'{outDir}/{self.module_name}-{str(self.module_version)}.gamod'
        
        self.step = Step.INITIATED
    
    def create(self):
        if self.step != Step.INITIATED:
            raise ValueError("Archive already created")
        
        Logger.info(f"starting creation of archive {self.archiveName}")
        self.__checkFolderContent()
        self.zipFile = ZipFile(self.archiveName, 'w')
        self.__addCode()
        self.__createJson()
        Logger.info(f"Archive {self.archiveName} created")
        self.step = Step.BUILT
    
    def __checkFolderContent(self):
        for requiredFile in ["server/main.js", "client/index.html"]:
            if not os.path.exists(f"{self.compiled_code_folder}/{requiredFile}"):
                raise ValueError(f"File {requiredFile} not found in {self.compiled_code_folder}")
           
    def __addCode(self):
        Logger.debug(f"Adding code from {self.compiled_code_folder} to zip")
        addFolderToZip(self.zipFile, "build", self.compiled_code_folder)
    
    def __createJson(self):
        Logger.debug(f"Creating json file for module {self.module_name} version {self.module_version}")
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
        self.zipFile.writestr('module.json', result)
        Logger.debug(f"Json file created:\n{result}")
    
    def __str__(self):
        return self.archiveName
