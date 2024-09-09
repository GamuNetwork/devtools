from gamuLogger import Logger
import sys, os
from tempfile import mkstemp

PYTHON = sys.executable
NULL_TARGET = '/dev/null' if os.name == 'posix' else 'nul'

Logger.setModule("Venv")

class Venv:
    __instance = None
    
    def __init__(self, path : str, workingDir : str):       
        self.__path = path
        self.__workingDir = workingDir
        
        Logger.deepDebug("executing command: " + f'{PYTHON} -m venv {path}')
        returnCode = os.system(f'{PYTHON} -m venv {path}')
        if returnCode != 0:
            Logger.error(f"Command {PYTHON} -m venv {path} failed with return code {returnCode}")
            sys.exit(returnCode)
        Logger.deepDebug(f"Command {PYTHON} -m venv {path} executed successfully")
        
        Venv.__instance = self
        
    def install(self, package : str, version = None):
        if version is not None:
            package += f'=={version}'
        Logger.debug(f"Installing package {package}")
        self.__run(f'python -m pip install {package}')
        Logger.debug(f"Package {package} installed successfully")
        return self #to chain the calls
        
    def InstallFromRequirements(self, path : str):
        Logger.debug(f"Installing packages from requirements file {path}")
        self.__run(f'python -m pip install -r {path}')
        Logger.debug(f"Packages installed successfully")
        
    def __run(self, command : str):
        stdoutFile, stdoutPath = mkstemp()
        stderrFile, stderrPath = mkstemp()
        
        cwd = os.getcwd()
        os.chdir(self.__workingDir)
        returnCode = os.system(f'{self.__path}/bin/{command} > {stdoutPath} 2> {stderrPath}')
        os.chdir(cwd)
        
        if returnCode != 0:
            Logger.error(f"Command {command} failed with return code {returnCode}")
            with open(stdoutPath, 'r') as file:
                Logger.debug('stdout:\n' + file.read())
            with open(stderrPath, 'r') as file:
                Logger.debug('stderr:\n' + file.read())
            
            os.remove(stdoutPath)
            os.remove(stderrPath)
                
            raise RuntimeError('Command failed')
        return returnCode
    
    def runExecutable(self, executable : str):
        Logger.debug(f"Running executable {executable} in virtual environment (working directory: {self.__workingDir})")
        self.__run(executable)
        Logger.debug(f"Executable {executable} executed successfully")
        return self
    
    def run(self, command : str):
        Logger.debug(f"Running command {command} in virutal environment (working directory: {self.__workingDir})")
        result = self.__run(f"python {command}")
        Logger.debug(f"Command {command} executed successfully")
        return self #to chain the calls
    
    def runModule(self, module : str):
        Logger.debug(f"Running module {module} in virtual environment (working directory: {self.__workingDir})")
        self.__run(f'python -m {module}')
        Logger.debug(f"Module {module} executed successfully")
        return self
        
    @property
    def python(self):
        return self.__path + '/bin/python'
    
    @property
    def pip(self):
        return self.__path + '/bin/pip'

    @property
    def path(self):
        return self.__path

    @staticmethod
    def getInstance(path : str, workingDir : str):
        if Venv.__instance is None:
            Logger.debug("Creating new Venv instance")
            Venv.__instance = Venv(path, workingDir)
        else:
            Logger.debug("Reusing existing Venv instance")
        return Venv.__instance