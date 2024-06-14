import argparse
from gamuLogger import Logger, LEVELS

import os, sys, shutil

from tempfile import mkdtemp

class BaseBuilder:
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
        buildersOptions.add_argument('--temp-dir', help='Temporary directory', type=str, default=mkdtemp())
        buildersOptions.add_argument('--dist-dir', help='Distribution directory', type=str, default='dist')
        buildersOptions.add_argument('-pv', '--package-version', help='Package version', type=str, default='0.0.0')
        
        self.argumentParser.add_argument('--version', '-v', action='version', version='%(prog)s 1.0')
        
        self.args = self.argumentParser.parse_args()
        
        if self.args.debug:
            Logger.setLevel('stdout', LEVELS.DEBUG)
        
        
        Logger.debug('Using temporary directory: ' + os.path.abspath(self.args.temp_dir))
        Logger.debug('Using distribution directory: ' + os.path.abspath(self.args.dist_dir))
        
        if os.path.exists(self.args.temp_dir):
            Logger.debug('Removing temp directory for cleaning')
            shutil.rmtree(self.args.temp_dir)
        
        Logger.debug('Creating temp directory')
        os.makedirs(self.args.temp_dir)
        
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
        
        
    
    # These methods should be overriden by the child class
    def Setup(self):
        """Copy required file to the temporary directory and replace the version string by the package version, install dependencies, etc."""
        Logger.warning('no setup configured')
    
    def Tests(self):
        """Run the tests for the package"""
        Logger.debug('no tests configured')
        
    def Docs(self):
        """Generate the documentation for the package"""
        Logger.debug('no docs configured')
        
    def Build(self):
        """Build the package"""
        Logger.warning('no build configured')
        
    def Publish(self):
        """Publish the package"""
        Logger.error('no publish configured')
        
        
    def __clean(self):
        shutil.rmtree(self.args.temp_dir)
        
    
    def __run(self):
        """
        Order of execution:
        - Setup
        - Build
        - Tests
        - Docs
        - Publish
        - Clean
        
        If any of this steps fails, the process should stop, and the clean method should be called
        """
        
        Logger.info('Running setup')
        self.Setup()
        Logger.debug('Setup finished')
        
        if not self.args.no_build:
            Logger.info('Building package')
            self.Build()
        
        if self.args.no_tests:
            Logger.warning('Skipping tests')
        else:
            Logger.info('Running tests')
            self.Tests()
        
        if not self.args.no_docs:
            Logger.info('Generating documentation')
            self.Docs()
        
        if self.args.publish:
            Logger.info('Publishing package')
            self.Publish()
        else:
            Logger.info('Package not published')
        
        if self.args.no_clean:
            Logger.warning('Skipping cleaning')
        else:
            Logger.info('Cleaning temporary files')
            self.__clean()
            Logger.debug('Temporary files cleaned')
            
        Logger.info('Process finished')


    @staticmethod
    def execute():
        subClasses = BaseBuilder.__subclasses__()
        if len(subClasses) == 0:
            Logger.critical('No builders found')
            sys.exit(1)
        elif len(subClasses) > 1:
            Logger.critical('Multiple builders found')
            sys.exit(1)
        subClasses[0]().__run()
        
        
# some useful constants
        
PYTHON = sys.executable
NULL_TARGET = '/dev/null' if os.name == 'posix' else 'nul'
