from enum import Enum
from json5 import loads
from datetime import datetime, timedelta

class PLATFORM(Enum):
    MACOS = "macos"
    WINDOWS = "windows"
    LINUX = "ubuntu"
    
    def __str__(self):
        return self.value
    
class PlatformData:
    Platforms = [PLATFORM.MACOS, PLATFORM.WINDOWS, PLATFORM.LINUX]
    @staticmethod
    def setPlatformList(platforms : list[PLATFORM]):
        PlatformData.Platforms = platforms
    @staticmethod
    def getPlatformList():
        return PlatformData.Platforms
    
    def __init__(self, **kwargs):
        if len(kwargs) != len(PlatformData.Platforms):
            raise ValueError("Invalid number of platforms; expected " + str(len(PlatformData.Platforms)) + " but got " + str(len(kwargs)))
    
        if not all(isinstance(value, type(next(iter(kwargs.values())))) for value in kwargs.values()):
            raise ValueError("All values must be of the same type; got " + str({type(value) for value in kwargs.values()}))
        
        self.data = {platform: kwargs[str(platform)] for platform in PlatformData.Platforms} #type: dict[PLATFORM, any]
        
    def getInOrder(self, order : list[PLATFORM]) -> list[any]:
        return [self[platform] for platform in order]
        
    def getType(self):
        return type(next(iter(self.data.values())))
        
    @staticmethod
    def from_dict(data : dict):
        return PlatformData(**data)
    
    def __getitem__(self, platform : PLATFORM|str):
        if isinstance(platform, PLATFORM):
            return self.data[platform]
        return self.data[PLATFORM(platform)]
    
    def __str__(self):
        return str(self.data)
    
    def __iter__(self):
        return iter(self.data)
    
    def __len__(self):
        return len(self.data)
    
    def items(self):
        return self.data.items()


class Suite:
    def __init__(self, json : str|dict, files : dict[str,dict[str, dict[str, str]]]):
        if isinstance(json, str):
            json = loads(json)
            
        # common fields
        self.id = json["id"]
        self.description = json["description"]
        self.fullName = json["fullName"]
        self.filename = json["filename"]
        
        # specific fields by platform
        # self.duration = Duration(json["duration"])
        # self.passed = json["passed"]
        # self.failed = json["failed"]
        # self.pending = json["pending"]
        # self.skipped = json["skipped"]
        # self.specs = [Spec(spec_json, self) for spec_json in json["specs"]]
        
        self.duration = PlatformData.from_dict({key: Duration(value["duration"]) for key, value in json['platforms'].items()})
        self.passed = PlatformData.from_dict({key: value["passed"] for key, value in json['platforms'].items()})
        self.failed = PlatformData.from_dict({key: value["failed"] for key, value in json['platforms'].items()})
        self.pending = PlatformData.from_dict({key: value["pending"] for key, value in json['platforms'].items()})
        self.skipped = PlatformData.from_dict({key: value["skipped"] for key, value in json['platforms'].items()})
        
        self.specs = [Spec(spec_json, self, files) for spec_json in json["specs"].values()]

        
    def __str__(self):
        return self.fullName
    
    @staticmethod
    def suiteForOrphans(orphansData : dict, files : dict[str,dict[str, dict[str, str]]]):
        return Suite({
            "id": "orphans",
            "description": "specs that are not in any suite",
            "fullName": "Specs that are not in any suite",
            "filename": "No specific file",
            
            "platforms": orphansData["platforms"],
            "specs": orphansData["specs"]
        },
        files)
    
class Spec:
    def __init__(self, json : str|dict, parentSuite : Suite|None, files : dict[str,dict[str, dict[str, str]]]):
        if isinstance(json, str):
            json = loads(json)
            
        self.id = json["id"]
        self.description = json["description"]
        self.fullName = json["fullName"]
        self.filename = json["filename"]
        self.parentSuite = parentSuite
        
        self.expectations = PlatformData.from_dict({key: [Expectation.from_json(expectation, files[key]) for expectation in value["failedExpectations"] + value["passedExpectations"]] for key, value in json['platforms'].items()})
        self.deprecationWarnings = PlatformData.from_dict({key: value["deprecationWarnings"] for key, value in json['platforms'].items()})
        self.duration = PlatformData.from_dict({key: Duration(value["duration"]) for key, value in json['platforms'].items()})
        self.status = PlatformData.from_dict({key: Status(value["status"]) if value["pendingReason"] != "Temporarily disabled with xit" else Status.SKIPPED for key, value in json['platforms'].items()})
        self.pendingReason = PlatformData.from_dict({key: value["pendingReason"] if self.status[key] == Status.PENDING else None for key, value in json['platforms'].items()})
        
    def __str__(self):
        return self.fullName

class Expectation:
    def __init__(self, json : str|dict, files : dict[str, dict[str, str]]):
        if isinstance(json, str):
            json = loads(json)
            
        self.matcherName = json["matcherName"]
        self.message = json["message"]
        self.stack = Stack(json["stack"], files)
        self.passed = json["passed"] #type: bool
        
    def __str__(self):
        return self.message
    
    @staticmethod
    def from_json(json : str|dict, files : dict[str, dict[str, str]]):
        if isinstance(json, str):
            json = loads(json)
            
        if json["passed"]:
            return PassedExpectation(json, files)
        else:
            return FailedExpectation(json, files)
    
class FailedExpectation(Expectation):
    def __init__(self, json : str|dict, files : dict[str, dict[str, str]]):
        super().__init__(json, files)
        self.expected = json["expected"]
        self.actual = json["actual"]

class PassedExpectation(Expectation):
    def __init__(self, json : str|dict, files : dict[str, dict[str, str]]):
        super().__init__(json, files)
        
class Status(Enum):
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    SKIPPED = "skipped"
    
    def __str__(self):
        return self.value
    
class Stack:
    class Position:
        def __init__(self, stackEntry : dict[str, str]):
            self.path = stackEntry["filePath"] if "filePath" in stackEntry else None
            self.line = int(stackEntry["lineNumber"]) if "lineNumber" in stackEntry else None
            self.column = int(stackEntry["columnNumber"]) if "columnNumber" in stackEntry else None
            
        def __str__(self):
            return f"{self.path}:{self.line}:{self.column}"
    
    def __init__(self, stack : list, files : dict[str, dict[str, str]]):
        self.stack = [] #type: list[Stack.Position]
        for stackEntry in stack:
            if stackEntry["filePath"]+":"+stackEntry["lineNumber"] in files.keys():
                self.stack.append(Stack.Position(stackEntry))
        
        self.files = {}
        for stackEntry in self.stack:
            if not stackEntry.path in self.files:
                self.files[stackEntry.path] = files[stackEntry.path+":"+str(stackEntry.line)]
                
    def get_context(self) -> dict[str, str]:
        # read contextSize lines before and after the last position in the stack
        # return the list of lines in the file
        lastPosition = self.get_last_position()
        if lastPosition is None:
            return None
        return self.files[lastPosition.path]
        
        
    
    def get_last_position(self) -> Position:
        contextPositionIndex = len(self.stack) - 1
        while contextPositionIndex >= 0 and self.stack[contextPositionIndex].path is None:
            contextPositionIndex -= 1
        if contextPositionIndex < 0:
            # raise ValueError("No position in the stack has a path")
            return None
        return self.stack[contextPositionIndex]

    def __str__(self):
        return "\n".join(str(position) for position in self.stack)
    
    def __iter__(self):
        return iter(self.stack)
    
    def __getitem__(self, index):
        return self.stack[index]
    
class Summary:
    def __init__(self, json : str|dict):
        if isinstance(json, str):
            json = loads(json)
            
        self.appName = json["appName"]
        self.appVersion = json["appVersion"]
        self.specs = json["specs"]
        self.failures = json["failures"]
        self.pending = json["pending"]
        self.duration = Duration(json["duration"])
        self.skipped = json["skipped"]
        self.passed = json["passed"]
        assert self.passed == self.specs - self.failures - self.pending - self.skipped # sanity check
        self.platforms = [PLATFORM(platform) for platform in json["platforms"]]
        self.startDate = datetime.fromisoformat(json["startDate"])
        self.endDate = self.startDate + self.duration.getTimeDelta()
        
        PlatformData.setPlatformList(self.platforms)
        
    def __str__(self):
        return f"{self.appName} {self.appVersion} - {self.startDate}"
    
class Duration:
    def __init__(self, milliseconds : int):
        self.milliseconds = milliseconds
    
    def __str__(self):
        if self.milliseconds < 1000:
            return f"{self.milliseconds} milliseconds"
        seconds = self.milliseconds / 1000
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        minutes = seconds / 60
        if minutes < 60:
            return f"{minutes:.2f} minutes"
        hours = minutes / 60
        return f"{hours:.2f} hours"

    def get(self):
        return self.__str__()
    
    def getTimeDelta(self):
        return timedelta(milliseconds=self.milliseconds)
