import argparse
import os, sys, shutil
from enum import Enum
from tempfile import mkdtemp, mkstemp

# some useful constants
        
PYTHON = sys.executable
NULL_TARGET = '/dev/null' if os.name == 'posix' else 'nul'

try:
    from gamuLogger import Logger, LEVELS, debugFunc
except ImportError:
    print("Logger not found, installing...", end=' ', flush=True)
    os.system(f'{sys.executable} -m pip install https://github.com/GamuNetwork/logger/releases/download/2.0.0-alpha.4/gamu_logger-2.0.0a4-py3-none-any.whl > {NULL_TARGET} 2> {NULL_TARGET}')
    print("done")
    from gamuLogger import Logger, LEVELS, debugFunc

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
    
    def __init__(self):
        if self.__class__ == BaseBuilder:
            raise Exception('BaseBuilder is an abstract class and cannot be instantiated')
        
        self.argumentParser = argparse.ArgumentParser(description='Builder tool')
        
        loggerOptions = self.argumentParser.add_argument_group('Logger options')
        loggerOptions.add_argument('--debug', action='store_true', help='Enable debug messages')
        
        buildersOptions = self.argumentParser.add_argument_group('Builder options')
        buildersOptions.add_argument('--no-tests', action='store_true', help='Do not run tests')
        buildersOptions.add_argument('--no-docs', action='store_true', help='Do not generate documentation')
        buildersOptions.add_argument('--no-build', action='store_true', help='Do not build the package')
        buildersOptions.add_argument('--publish', action='store_true', help='Publish the package')
        buildersOptions.add_argument('--no-clean', action='store_true', help='Do not clean temporary files')
        buildersOptions.add_argument('--temp-dir', help='Temporary directory (used to generate the package)', type=str, default=mkdtemp())
        buildersOptions.add_argument('--dist-dir', help='Distribution directory (where to save the built files)', type=str, default='dist')
        buildersOptions.add_argument('-pv', '--package-version', help='set the version of the package you want to build', type=str, default='0.0.0')
        
        self.argumentParser.add_argument('--version', '-v', action='version', version='%(prog)s 1.0')
        
        self.args = self.argumentParser.parse_args()
        
        self.__steps = {
            "Setup": self.Status.WAITING,
            "Build": self.Status.DISABLED    if self.args.no_build   else self.Status.WAITING,
            "Tests": self.Status.DISABLED    if self.args.no_tests   else self.Status.WAITING,
            "Docs": self.Status.DISABLED     if self.args.no_docs    else self.Status.WAITING,
            "Publish": self.Status.WAITING   if self.args.publish    else self.Status.DISABLED
        }
        
        self.clean = not self.args.no_clean
        
        self.__remainingSteps = len([step for step in self.__steps if self.__steps[step] != self.Status.DISABLED])
        
        self.__stepDependencies = {
            "Setup": [],
            "Build": ["Setup"],
            "Docs": ["Setup"],
            "Tests": ["Setup", "Build"],
            "Publish": ["Setup", "Build", "Tests", "Docs"]
        }
        
        if self.args.debug:
            Logger.setLevel('stdout', LEVELS.DEBUG)
        
        
        Logger.debug('Using temporary directory: ' + os.path.abspath(self.args.temp_dir))
        Logger.debug('Using distribution directory: ' + os.path.abspath(self.args.dist_dir))
        
    @property
    def tempDir(self):
        return os.path.abspath(self.args.temp_dir)
    
    @property
    def packageVersion(self):
        return self.args.package_version
    
    @property
    def distDir(self):
        return os.path.abspath(self.args.dist_dir)
    
    def CopyAndReplaceByPackageVersion(self, src, dst, versionString = "{version}"):
        with open(src, 'r') as file:
            content = file.read()
        content = content.replace(versionString, self.packageVersion)
        with open(dst, 'w') as file:
            file.write(content)
        
    def runCommand(self, command) -> bool:
        Logger.debug('Executing command: ' + command)
        stdoutFile, stdoutPath = mkstemp()
        stderrFile, stderrPath = mkstemp()
        returnCode = os.system(f'{command} > {stdoutPath} 2> {stderrPath}')
        if returnCode != 0:
            Logger.error(f'Task failed successfully with return code {returnCode}') # this is for the joke
            with open(stdoutPath, 'r') as file:
                Logger.debug('stdout: ' + file.read())
            with open(stderrPath, 'r') as file:
                Logger.debug('stderr: ' + file.read())
            
            os.remove(stdoutPath)
            os.remove(stderrPath)
            return False
        else:
            Logger.debug('Command executed successfully')
            os.remove(stdoutPath)
            os.remove(stderrPath)
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
        for dependency in self.__stepDependencies[step]:
            if self.__steps[dependency] != self.Status.FINISHED:
                return False
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
            return False
        else:
            if hasSucceeded is None:
                Logger.warning('Step "' + step + '" did not return a value, but didn\'t throw anything, assuming it has succeeded')
                return True
            return hasSucceeded
    
    def __run(self, configuredSteps : list[str]):
        for step in self.__steps:
            if step not in configuredSteps and step != '__clean':
                self.__steps[step] = self.Status.DISABLED
                self.__remainingSteps -= 1
                Logger.debug('Step "' + step + '" disabled')
        
        
        HasFailed = False
        while self.__remainingSteps > 0 and not HasFailed:
            for step in self.__steps:
                if self.__steps[step] == self.Status.WAITING and self.__canStepBeStarted(step):
                    Logger.info('Starting step "' + step + '"')
                    self.__steps[step] = self.Status.RUNNING
                    
                    hasSucceeded = self.__runStep(step)
                        
                    if hasSucceeded:
                        self.__steps[step] = self.Status.FINISHED
                        self.__remainingSteps -= 1
                    else:
                        self.__steps[step] = self.Status.FAILED
                        Logger.error('Step "' + step + '" failed')
                        HasFailed = True
                        break

        if self.clean:
            self.__clean()
                    
        if HasFailed:
            Logger.critical('A step has failed')
            sys.exit(1)
        else:
            Logger.info('Build finished successfully')


    @staticmethod
    def execute():
        subClasses = BaseBuilder.__subclasses__()
        if len(subClasses) == 0:
            Logger.critical('No builders found')
            sys.exit(1)
        elif len(subClasses) > 1:
            Logger.critical('Multiple builders found')
            sys.exit(1)
            
        possibleSteps = ['Setup', 'Tests', 'Docs', 'Build', 'Publish']
        steps = [step for step in subClasses[0].__dict__ if step in possibleSteps]
        subClasses[0]().__run(steps)
        
        
