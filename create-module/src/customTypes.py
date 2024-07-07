from enum import Enum

class Version:
    def __init__(self, major : int, minor : int = 0, revision : int = 0):
        self.major = major
        self.minor = minor
        self.revision = revision
    
    def __str__(self):
        return f"{self.major}.{self.minor}.{self.revision}"
    
    def __eq__(self, other):
        return self.major == other.major and self.minor == other.minor and self.revision == other.revision
    
    def __lt__(self, other):
        if self.major < other.major:
            return True
        elif self.major == other.major:
            if self.minor < other.minor:
                return True
            elif self.minor == other.minor:
                return self.revision < other.revision
        return False
    
    def __gt__(self, other):
        if self.major > other.major:
            return True
        elif self.major == other.major:
            if self.minor > other.minor:
                return True
            elif self.minor == other.minor:
                return self.revision > other.revision
        return False
    
    def __le__(self, other):
        return self < other or self == other
    
    def __ge__(self, other):
        return self > other or self == other
    
    def __ne__(self, other):
        return not self == other
    
    def nextMajor(self):
        return Version(self.major + 1)
    
    def nextMinor(self):
        return Version(self.major, self.minor + 1)
    
    def nextRevision(self):
        return Version(self.major, self.minor, self.revision + 1)
    
    @staticmethod
    def fromString(version):
        major, minor, revision = version.split(".")
        return Version(int(major), int(minor), int(revision))
    
    @staticmethod
    def isValid(version):
        try:
            Version.fromString(version)
            return True
        except:
            return False    

class ModuleTypes(Enum):
    GAME = 1
    INTERFACE = 2
    OTHER = 3
    
    def __str__(self) -> str:
        return self.name.lower()
    
    @staticmethod
    def fromString(type : str) -> 'ModuleTypes':
        type = type.lower()
        if type == "game":
            return ModuleTypes.GAME
        elif type == "interface":
            return ModuleTypes.INTERFACE
        else:
            return ModuleTypes.OTHER
        
class Step(Enum):
    INITIATED = 1
    BUILT = 2
    