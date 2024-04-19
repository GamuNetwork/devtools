import os
from typing import Callable
from dataTypes import Suite, Summary, Spec, Status, Stack, PlatformData, PLATFORM, Status
from json5 import dumps

#for file and folder operations
import shutil


def clearFolder(folder):
    """
    Clear the contents of a folder or create it if it doesn't exist
    After calling this function, the folder will be empty, but it will still exist
    """
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

def load_template(file, **kwargs):
    with open(file, "r") as f:
        template = f.read() #type: str
    for key, value in kwargs.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template

def getIcon(string : str):
    match string.lower():
        case "macos":
            return "apple"
        case "passed":
            return "check"
        case "failed":
            return "xmark"
        case "pending":
            return "clock"
        case "skipped":
            return "forward"
        case _:
            return string
        
        
def write_file_wrapper(output_dir) -> Callable[[str, str], None]: #used to pass the output directory to the function, so that it doesn't have to be passed every time
    def write_file(file, content):
        file = os.path.join(output_dir, file)
        if not os.path.exists(os.path.dirname(file)):
            os.makedirs(os.path.dirname(file))
        with open(file, "w") as f:
            f.write(content)
    return write_file

def getColorClass(status : Status) -> str:
    match status:
        case Status.PASSED:
            return "success"
        case Status.FAILED:
            return "error"
        case Status.PENDING:
            return "warning"
        case Status.SKIPPED:
            return "info"
        case _:
            return "secondary"

def toJson(obj):
    return dumps(obj, trailing_commas=False, quote_keys=True)


def getStatusTotal(status : PlatformData) -> Status:
    #order of precedence: FAILED > PENDING > PASSED > SKIPPED
    result = Status.SKIPPED
    for key, value in status.items():
        if value == Status.FAILED:
            return Status.FAILED
        elif value == Status.PENDING:
            result = Status.PENDING
        elif value == Status.PASSED and result != Status.PENDING:
            result = Status.PASSED
    return result

def getStatusFromSuite(suite : Suite) -> Status:
    #order of precedence: FAILED > PENDING > PASSED > SKIPPED
    result = Status.SKIPPED
    for spec in suite.specs:
        status = getStatusTotal(spec.status)
        if status == Status.FAILED:
            return Status.FAILED
        elif status == Status.PENDING:
            result = Status.PENDING
        elif status == Status.PASSED and result != Status.PENDING:
            result = Status.PASSED
    return result
