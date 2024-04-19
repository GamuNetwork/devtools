import os
import sys
from time import sleep
import re
import subprocess as sp

FILES = {} #type: dict[str, int] # {file: timestamp}

FILTER = r"(\.\\\w*\.py$)|(\.\\resources\\.*\.template\.html$)"


def getFiles() -> list[str]:
    files = []
    for root, _, filenames in os.walk("."):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            if re.match(FILTER, filepath):
                files.append(filepath)
    
    return files

def getLastModified(file: str) -> int:
    return os.path.getmtime(file)


def main():
    FILES = {file: getLastModified(file) for file in getFiles()}
    print(f"Watching {len(FILES)} files")
    
    while True:
        modified = False
        for file in getFiles():
            if file not in FILES:
                FILES[file] = getLastModified(file)
                print(f"New file {file}")
                modified = True
            elif getLastModified(file) != FILES[file]:
                FILES[file] = getLastModified(file)
                print(f"File {file} modified")
                modified = True
        
        temp = FILES.copy()
        for file in FILES:
            if file not in getFiles():
                print(f"File {file} deleted")
                del temp[file]
                modified = True
        FILES = temp
        
        if modified:
            print() # Empty line
            response = sp.run([sys.executable, "main.py", "output.json"])
            if response.returncode == 0:
                print("Report generated")
            else:
                print("Error generating report")
        sleep(1)
    
if __name__ == "__main__":
    main()