from src.builder-tool import BaseBuilder, Logger, PYTHON, NULL_TARGET #this file use the module to build itself
import os
import shutil


class Builder(BaseBuilder):
    def Setup(self):
        Logger.debug('Copying sources')
        shutil.copytree('src', self.tempDir + '/src', ignore=shutil.ignore_patterns('*.pyc', '*.pyo', '__pycache__'))
        Logger.debug('Copying pyproject.toml')
        self.CopyAndReplaceByPackageVersion('pyproject.toml', self.tempDir + '/pyproject.toml')
        Logger.debug('Copying requirements.txt')
        shutil.copy('requirements.txt', self.tempDir + '/requirements.txt')
        Logger.debug('Copying readme.md')
        self.CopyAndReplaceByPackageVersion('readme.md', self.tempDir + '/readme.md')
        
    def Build(self):
        command = f'{PYTHON} -m build --outdir {self.distDir} {self.tempDir} > {NULL_TARGET}'
        Logger.debug('Executing command: ' + command)
        os.system(command)
        

BaseBuilder.execute()
