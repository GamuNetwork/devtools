import argparse
from .createModule import Archive
from .customTypes import Version, ModuleTypes
from gamuLogger import Logger, error, info, critical, LEVELS

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
    parser.add_argument("--outDir", "-o", help="The output directory for the archive", default=".")
    parser.add_argument("--branch", help="The branch of the repository", default="main")
    parser.add_argument("--debug", "-d", help="Enable debug mode", action="store_true")
    return parser

Logger.setModule("createModule")

info("Starting module creation")


parser = createParser()
args = parser.parse_args()

if args.debug:
    Logger.setLevel("stdout", LEVELS.DEBUG)

module_version = Version.fromString(args.module_version)
module_type = ModuleTypes.fromString(args.module_type)

info(f"Creating archive for module {args.module_name} version {module_version}")

archive = Archive(args.outDir, args.compiled_code_folder, args.module_name, module_version, module_type, args.module_description, args.module_author, args.branch)
    
try:
    archive.create()
except Exception as e:
    critical(f"Error creating module: {str(e)}")
    exit(1)
else:
    info(f"Archive created: {archive}")
    info(f"MD5: {archive.getMD5()}")
    exit(0)
