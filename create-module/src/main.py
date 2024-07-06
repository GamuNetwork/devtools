
from zipfile import ZipFile
import os
import json
from datetime import datetime
from customTypes import Version, ModuleTypes

from gamuLogger import debug, info, error, critical, Logger, LEVELS

def parseModuleNames(module_name: str):
    # GamuNetwork/ModuleName -> ModuleName
    return module_name.replace("\\", "/").split("/")[-1]

def createJson(module_name, module_version : Version, module_type : ModuleTypes, module_description, module_author, branch = "main"):
    debug(f"Creating json file for module {module_name} version {module_version}")
    module = {
        "name": module_name,
        "version": str(module_version),
        "type": str(module_type),
        "description": module_description,
        "author": module_author,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "repository": f"https://github.com/GamuNetwork/{module_name}",
        "branch": branch
    }
    result = json.dumps(module, indent=4)
    debug(f"Json file created: {result}")
    return result

def addFolderToZip(zip: ZipFile, arc_path, folder, parent_folder = ""):
    debug(f"Adding folder {folder} to zip")
    for file in os.listdir(folder):
        file_path = os.path.join(folder, file)
        if os.path.isfile(file_path):
            debug(f"Adding file {file} to zip")
            zip.write(file_path, os.path.join(arc_path, parent_folder, file))
        elif os.path.isdir(file_path):
            addFolderToZip(zip, arc_path, file_path, os.path.join(parent_folder, file))

def createArchive(compiled_code_folder, module_name, module_version : Version, module_type : ModuleTypes, module_description, module_author, branch = "main"):
    with ZipFile(f'{module_name}-{str(module_version)}.gamod', 'w') as zip:
        addFolderToZip(zip, "build", compiled_code_folder)
        debug(f"Compiled code folder added to archive")
        zip.writestr('module.json', createJson(module_name, module_version, module_type, module_description, module_author, branch))
        debug(f"Json file added to archive")
    
    return f'{module_name}-{str(module_version)}.gamod'

if __name__ == "__main__":
    import argparse
    
    def handleParserError(message):
        error(message)
        raise ValueError("Invalid arguments")
    
    def createParser():
        parser = argparse.ArgumentParser(description="Create a module archive")
        parser.error = handleParserError
        parser.add_argument("compiled_code_folder", help="The compiled code folder (dist folder for javascript)")
        parser.add_argument("module_name", help="The module name")
        parser.add_argument("module_version", help="The module version")
        parser.add_argument("module_type", help="The module type")
        parser.add_argument("module_description", help="The module description")
        parser.add_argument("module_author", help="The module author")
        parser.add_argument("--branch", help="The branch of the repository", default="main")
        parser.add_argument("--debug", "-d", help="Enable debug mode", action="store_true")
        return parser
    
    info("Starting module creation")
    
    try:
        parser = createParser()
        args = parser.parse_args()
        
        if args.debug:
            Logger.setLevel("stdout", LEVELS.DEBUG)
    
        module_version = Version.fromString(args.module_version)
        module_type = ModuleTypes.fromString(args.module_type)

        info(f"Creating archive for module {args.module_name} version {module_version}")
        
        createArchive(args.compiled_code_folder, parseModuleNames(args.module_name), module_version, module_type, args.module_description, args.module_author, args.branch)
    
    except Exception as e:
        critical(f"Error creating module: {str(e)}")
        exit(1)
    
    info(f"Archive created: {args.module_name}-{str(module_version)}.gamod")
    exit(0)
