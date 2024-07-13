import argparse
import os, sys, shutil
from enum import Enum
from tempfile import mkdtemp, mkstemp

# some useful constants
        
PYTHON = sys.executable
NULL_TARGET = '/dev/null' if os.name == 'posix' else 'nul'

try:
    from gamuLogger import Logger, LEVELS, debugFunc
    import gamuLogger
    
    if gamuLogger.__version__ < '2.0.1':
        raise ImportError('Logger version is too old')
    
except (ImportError, AttributeError):
    print("Logger not found, installing...", end=' ', flush=True)
    os.system(f'{sys.executable} -m pip install https://github.com/GamuNetwork/logger/releases/download/2.0.1/gamu_logger-2.0.1-py3-none-any.whl > {NULL_TARGET} 2> {NULL_TARGET}')
    print("done")
    from gamuLogger import Logger, LEVELS, debugFunc
    import gamuLogger
    
Logger.setModule('Builder')

class BaseBuilder:
    """
    Create a new builder by subclassing this class and implementing the steps as methods
    steps are:
    - Setup
    - Build
    - Tests
    - Docs
    - Publish
    
    example:
    ```python
    class Builder(BaseBuilder):
        def Setup(self):
            # do something
            
        def Build(self):
            # do something
            
    BaseBuilder.execute() #this will run the steps
    ```
    
    Use `python {your_script}.py -h` to see the available options
    """
    class Status(Enum):
        WAITING = 0
        RUNNING = 1
        FINISHED = 2
        FAILED = 3
        DISABLED = 4
        
        def __str__(self):
            return self.name
        
    class RequireMode(Enum):
        OPTIONAL = 0
        REQUIRED = 1
        
        def __str__(self):
            return self.name
    
    def __init__(self):
        if self.__class__ == BaseBuilder:
            raise Exception('BaseBuilder is an abstract class and cannot be instantiated')
        
        self.argumentParser = argparse.ArgumentParser(description='Builder tool')
        
        loggerOptions = self.argumentParser.add_mutually_exclusive_group()
        loggerOptions.add_argument('--debug', action='store_true', help='Enable debug messages')
        loggerOptions.add_argument('--deep-debug', action='store_true', help='Enable deep debug messages')
        
        buildersOptions = self.argumentParser.add_argument_group('Builder options')
        buildersOptions.add_argument('--no-tests', action='store_true', help='Do not run tests')
        buildersOptions.add_argument('--no-docs', action='store_true', help='Do not generate documentation')
        buildersOptions.add_argument('--publish', action='store_true', help='Publish the package')
        buildersOptions.add_argument('--no-clean', action='store_true', help='Do not clean temporary files')
        buildersOptions.add_argument('--temp-dir', help='Temporary directory (used to generate the package)', type=str, default=mkdtemp())
        buildersOptions.add_argument('--dist-dir', help='Distribution directory (where to save the built files)', type=str, default='dist')
        buildersOptions.add_argument('-pv', '--package-version', help='set the version of the package you want to build', type=str, default='0.0.0')
        
        self.argumentParser.add_argument('--version', '-v', action='version', version='%(prog)s 1.0')
        
        self.args = self.argumentParser.parse_args()
        
        self.__steps = {
            "Setup":        self.Status.WAITING,
            "Build":        self.Status.WAITING,
            "Tests":        self.Status.DISABLED    if self.args.no_tests   else self.Status.WAITING,
            "BuildTests" :  self.Status.DISABLED    if self.args.no_tests   else self.Status.WAITING,
            "Docs":         self.Status.DISABLED    if self.args.no_docs    else self.Status.WAITING,
            "Publish":      self.Status.WAITING     if self.args.publish    else self.Status.DISABLED
        }
        
        self.clean = not self.args.no_clean
        
        self.__remainingSteps = [step for step in self.__steps if self.__steps[step] != self.Status.DISABLED]
        
        self.__stepDependencies = {
            "Setup": {},
            "Build": {
                "Setup" : self.RequireMode.REQUIRED,
                "Tests" : self.RequireMode.OPTIONAL
            },
            "Docs": {
                "Setup" : self.RequireMode.REQUIRED
            },
            "Tests": {
                "Setup" : self.RequireMode.REQUIRED
            },
            "BuildTests": {
                "Setup" : self.RequireMode.REQUIRED,
                "Build" : self.RequireMode.REQUIRED
            },
            "Publish": {
                "Build" : self.RequireMode.REQUIRED,
                "BuildTests" : self.RequireMode.OPTIONAL,
                "Docs" : self.RequireMode.OPTIONAL
            }
        } #type: dict[str, dict[str, BaseBuilder.RequireMode]]
        
        self.debugLevel = LEVELS.INFO
        
        if self.args.debug:
            self.debugLevel = LEVELS.DEBUG
        elif self.args.deep_debug:
            self.debugLevel = LEVELS.DEEP_DEBUG
            
        Logger.setLevel('stdout', self.debugLevel)
        
        
        Logger.debug("Using gamuLogger version : " + gamuLogger.__version__)
        Logger.debug('Using temporary directory: ' + os.path.abspath(self.args.temp_dir))
        Logger.debug('Using distribution directory: ' + os.path.abspath(self.args.dist_dir))
        
        # clear the dist directory
        try:
            shutil.rmtree(self.args.dist_dir)
        except FileNotFoundError:
            pass
        except Exception as e:
            Logger.error('Error while cleaning dist directory: ' + str(e))
            sys.exit(1)
        
        os.makedirs(self.args.dist_dir, exist_ok=True)
        
    @property
    def tempDir(self):
        return os.path.abspath(self.args.temp_dir)
    
    @property
    def packageVersion(self):
        return self.args.package_version
    
    @property
    def distDir(self):
        return os.path.abspath(self.args.dist_dir)
    
    def addAndReplaceByPackageVersion(self, src, dest = None, versionString = "{version}"):
        """Add a file to the temporary directory and replace a string by the package version"""
        Logger.debug('Adding file: ' + src + ' and replacing version string by ' + self.packageVersion)
        with open(src, 'r') as file:
            content = file.read()
        content = content.replace(versionString, self.packageVersion)
        if dest is None:
            dest = src
        with open(self.tempDir + '/' + dest, 'w') as file:
            file.write(content)
        return True
        
    def runCommand(self, command : str, hideOutput = True, debugArg = "", deepDebugArg : str = None) -> bool:
        """
        Execute a command in the temporary directory\n
        Default value for deepDebugArg is the same as debugArg
        """
        if self.debugLevel == LEVELS.DEBUG:
            command += " " + debugArg
        elif self.debugLevel == LEVELS.DEEP_DEBUG:
            command += " " + (deepDebugArg if deepDebugArg is not None else debugArg)
        Logger.debug(f'Executing command {command}\n    working directory: {self.tempDir}')
        if hideOutput:
            stdoutFile, stdoutPath = mkstemp()
            stderrFile, stderrPath = mkstemp()
        
            cwd = os.getcwd()
            os.chdir(self.tempDir)
            returnCode = os.system(f'{command} > {stdoutPath} 2> {stderrPath}')
            os.chdir(cwd)
            
            if returnCode != 0:
                Logger.error(f'Task failed with return code {returnCode}')
                with open(stdoutPath, 'r') as file:
                    Logger.debug('stdout:\n' + file.read())
                with open(stderrPath, 'r') as file:
                    Logger.debug('stderr:\n' + file.read())
                
                os.remove(stdoutPath)
                os.remove(stderrPath)
                raise RuntimeError('Command failed')
            else:
                Logger.debug('Command executed successfully')
                os.remove(stdoutPath)
                os.remove(stderrPath)
                return True
            
        else:
            returnCode = os.system(f'{command}')
            if returnCode != 0:
                Logger.error(f'Task failed with return code {returnCode}')
                raise RuntimeError('Command failed')
            else:
                Logger.debug('Command executed successfully')
                return True
        
        
    def addFile(self, path, dest = None):
        """Copy a file to the temporary directory"""
        Logger.debug('Adding file: ' + path)
        if dest is None:
            dest = path
        shutil.copy(path, self.tempDir + '/' + dest)
        return True
        
        
    def addDirectory(self, path, dest = None):
        """Copy a directory to the temporary directory"""
        Logger.debug('Adding directory: ' + path)
        if dest is None:
            dest = path
        shutil.copytree(path, self.tempDir + '/' + dest, ignore=shutil.ignore_patterns('*.pyc', '*.pyo', '__pycache__'))
        return True
        
    def exportFile(self, path, dest = None):
        """Copy a file from the temporary directory to the distribution directory"""
        Logger.debug('Exporting file: ' + path)
        if dest is None:
            dest = path
        shutil.copy(self.tempDir + '/' + path, self.distDir + '/' + dest)
        return True
    
    def exportFolder(self, path, dest = None):
        """Copy a directory from the temporary directory to the distribution directory"""
        Logger.debug('Exporting directory: ' + path)
        if dest is None:
            dest = path
        shutil.copytree(self.tempDir + '/' + path, self.distDir + '/' + dest)
        return True
        
    def __clean(self) -> bool:
        Logger.info('Cleaning temporary directory')
        try:
            shutil.rmtree(self.args.temp_dir)
        except Exception as e:
            Logger.error('Error while cleaning temp directory: ' + str(e))
            return False
        else:
            Logger.debug('Temporary directory cleaned')
            return True
        
    
    def __canStepBeStarted(self, step):
        # a better version of the previous function
        for dependency, requireMode in self.__stepDependencies[step].items():
            match self.__steps[dependency]:
                case self.Status.WAITING:
                    Logger.deepDebug(f"The step '{step}' cannot be started because the dependency '{dependency}' is not started yet")
                    return False
                case self.Status.RUNNING:
                    Logger.deepDebug(f"The step '{step}' cannot be started because the dependency '{dependency}' is running and need to finish first")
                    return False
                case self.Status.FAILED:
                    Logger.deepDebug(f"The step '{step}' cannot be started because the dependency '{dependency}' has failed")
                    return False
                case self.Status.DISABLED:
                    if requireMode == self.RequireMode.REQUIRED:
                        Logger.deepDebug(f"The step '{step}' cannot be started because the dependency '{dependency}' is disabled but required")
                        return False
                    else:
                        Logger.deepDebug(f"The step '{step}' will run without the optional dependency '{dependency}'")
                        continue
                case self.Status.FINISHED:
                    continue
        return True
    
    
    def __runStep(self, step : str):
        '''
        A step is considered failed if it raises an exception, or if it returns False
        If it returns None, it is considered successful, but raises a warning
        '''
        hasSucceeded = False
        try:
            hasSucceeded = getattr(self, step)()
        except Exception as e:
            Logger.error('Step "' + step + '" raised an exception: ' + str(e))
            return False
        else:
            if hasSucceeded is None:
                return True
            return hasSucceeded
        
    def __listExport(self):
        files = []
        for root, _, filenames in os.walk(self.distDir):
            for filename in filenames:
                abspath = os.path.join(root, filename)
                files.append(abspath.replace(self.distDir+'/', ''))
        return files
    
    def __run(self, configuredSteps : list[str]):
        for step in self.__steps:
            if step not in configuredSteps:
                self.__steps[step] = self.Status.DISABLED
                if step in self.__remainingSteps:
                    self.__remainingSteps.remove(step)
                Logger.debug('Step "' + step + '" disabled')
        
        
        HasFailed = False
        while len(self.__remainingSteps) > 0 and not HasFailed:
            for step in self.__steps:
                if self.__steps[step] == self.Status.DISABLED:
                    continue
                Logger.deepDebug(f"evaluating step {step}\nremaining : " + str(self.__remainingSteps))
                if self.__steps[step] == self.Status.WAITING and self.__canStepBeStarted(step):
                    Logger.info('Starting step "' + step + '"')
                    self.__steps[step] = self.Status.RUNNING
                    
                    hasSucceeded = self.__runStep(step)
                    Logger.deepDebug('Step "' + step + '" returned ' + str(hasSucceeded))
                        
                    if hasSucceeded:
                        self.__steps[step] = self.Status.FINISHED
                        self.__remainingSteps.remove(step)
                    else:
                        self.__steps[step] = self.Status.FAILED
                        Logger.error('Step "' + step + '" failed')
                        HasFailed = True
                        break

        if self.clean:
            self.__clean()
        else:
            Logger.warning(f'Directory {self.tempDir} wasn\'t deleted because cleaning is disabled')
                    
        if HasFailed:
            Logger.critical('A step has failed')
            sys.exit(1)
        else:
            Logger.info('Build finished successfully')
            Logger.info("exported files:\n\t"+ "\n\t".join(self.__listExport()))


    @staticmethod
    def execute():
        subClasses = BaseBuilder.__subclasses__()
        if len(subClasses) == 0:
            Logger.critical('No builders found')
            sys.exit(1)
        elif len(subClasses) > 1:
            Logger.critical('Multiple builders found')
            sys.exit(1)
            
        possibleSteps = ['Setup', 'Tests', 'BuildTests', 'Docs', 'Build', 'Publish']
        steps = [step for step in subClasses[0].__dict__ if step in possibleSteps]
        subClasses[0]().__run(steps)
    
        
