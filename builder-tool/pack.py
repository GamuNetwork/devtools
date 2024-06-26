from src.builderTool import BaseBuilder, Logger, PYTHON #this file use the module to build itself


class Builder(BaseBuilder):
    def Setup(self):
        self.addDirectory('src')
        self.addAndReplaceByPackageVersion('pyproject.toml')
        self.addAndReplaceByPackageVersion('readme.md')
        self.runCommand(f'{PYTHON} -m pip install --upgrade build')
        
    def Build(self):
        self.runCommand(f'{PYTHON} -m build --outdir {self.distDir} .')
        

BaseBuilder.execute()
