from src.builderTool import BaseBuilder, Logger, PYTHON, NULL_TARGET #this file use the module to build itself


class Builder(BaseBuilder):
    def Setup(self):
        self.addDirectory('src')
        self.addAndReplaceByPackageVersion('pyproject.toml', self.tempDir + '/pyproject.toml')
        self.addFile("requirements.txt")
        self.addAndReplaceByPackageVersion('readme.md', self.tempDir + '/readme.md')
        
        
    def Build(self):
        self.runCommand(f'{PYTHON} -m build --outdir {self.distDir} {self.tempDir} > {NULL_TARGET}')
    
    def Publish(self):
        Logger.info("Publishing package")

BaseBuilder.execute()
