from builderTool import BaseBuilder, PYTHON #this file use the module to build itself


class Builder(BaseBuilder):
    def Setup(self):
        self.addDirectory('src', 'src/createModule')
        self.addAndReplaceByPackageVersion('pyproject.toml')
        self.runCommand(f'{PYTHON} -m pip install --upgrade build')
        
    def Build(self):
        self.runCommand(f'{PYTHON} -m build --outdir {self.distDir} .')
