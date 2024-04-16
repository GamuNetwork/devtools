from enum import Enum
from json5 import loads
from datetime import datetime, timedelta
import re

class Suite:
    def __init__(self, json : str|dict):
        if isinstance(json, str):
            json = loads(json)
            
        self.id = json["id"]
        self.description = json["description"]
        self.fullName = json["fullName"]
        self.filename = json["filename"]
        self.duration = Duration(json["duration"])
        self.properties = json["properties"]
        self.passed = json["passed"]
        self.failed = json["failed"]
        self.pending = json["pending"]
        self.skipped = json["skipped"]
        self.specs = [Spec(spec_json, self) for spec_json in json["specs"]]
        
    def __str__(self):
        return self.fullName
    
class Spec:
    def __init__(self, json : str|dict, parentSuite : Suite):
        if isinstance(json, str):
            json = loads(json)
            
        self.id = json["id"]
        self.description = json["description"]
        self.fullName = json["fullName"]
        self.filename = json["filename"]
        self.parentSuite = parentSuite
        self.expectations = [] #type: list[Expectation]
        for expectation in json["failedExpectations"]:
            self.expectations.append(Expectation.from_json(expectation))
        for expectation in json["passedExpectations"]:
            self.expectations.append(Expectation.from_json(expectation))
        self.deprecationWarnings = json["deprecationWarnings"]
        self.duration = Duration(json["duration"])
        self.properties = json["properties"]
        self.status = Status(json["status"]) if json["pendingReason"] != "Temporarily disabled with xit" else Status.SKIPPED
        self.pendingReason = json["pendingReason"] if self.status == Status.PENDING else None
        
    def __str__(self):
        return self.fullName

class Expectation:
    def __init__(self, json : str|dict):
        if isinstance(json, str):
            json = loads(json)
            
        self.matcherName = json["matcherName"]
        self.message = json["message"]
        self.stack = Stack(json["stack"])
        self.passed = json["passed"] #type: bool
        
    def __str__(self):
        return self.message
    
    @staticmethod
    def from_json(json : str|dict):
        if isinstance(json, str):
            json = loads(json)
            
        if json["passed"]:
            return PassedExpectation(json)
        else:
            return FailedExpectation(json)
    
class FailedExpectation(Expectation):
    def __init__(self, json : str|dict):
        super().__init__(json)
        self.expected = json["expected"]
        self.actual = json["actual"]

class PassedExpectation(Expectation):
    def __init__(self, json : str|dict):
        super().__init__(json)
        
class Status(Enum):
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    SKIPPED = "skipped"
    
    def __str__(self):
        return self.value
    
class Stack:
    class Position:
        def __init__(self, position : str):
            if position == "(<unknown>)":
                self.path = None #type: str
                self.line = None #type: int
                self.column = None #type: int
                return
            
            self.path, self.line, self.column = re.match(r"(.+):(\d+):(\d+)", position).groups()
            self.line = int(self.line)
            self.column = int(self.column)
            self.path = self.path.split('(')[-1]
            
        def __str__(self):
            return f"{self.path}:{self.line}:{self.column}"
    
    def __init__(self, string : str):
        self.stack = [] #type: list[Stack.Position]
        for line in string.split("\n"):
            line = line.strip()
            if line.count("(") == 1 and line.count(")") == 1:
                self.stack.append(self.Position(line))
            elif line != "":
                self.stack.append(self.Position("(<unknown>)"))
                
    def get_context(self, contextSize : int = 5) -> list[tuple[int, str]]:
        # read contextSize lines before and after the last position in the stack
        # return the list of lines in the file
        lastPosition = self.get_last_position()
        
        lines = [] #type: list[tuple[int, str]]
        with open(lastPosition.path, "r") as f:
            for i, line in enumerate(f):
                if i >= lastPosition.line - contextSize and i <= lastPosition.line + contextSize:
                    lines.append((i, line))
        
        return lines
    
    def get_last_position(self) -> Position:
        contextPositionIndex = len(self.stack) - 1
        while contextPositionIndex >= 0 and self.stack[contextPositionIndex].path is None:
            contextPositionIndex -= 1
        if contextPositionIndex < 0:
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
        self.startDate = datetime.fromisoformat(json["startDate"])
        self.endDate = self.startDate + self.duration.getTimeDelta()
        
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
    
if __name__ == "__main__":
    with open("report.json", "r") as f:
        data = f.read()
        
    data = loads(data) #type: dict[str, dict]
    
    suites = [Suite(suite) for suite in data["suites"].values()]
    for suite in suites:
        print(suite)
        for spec in suite.specs:
            print(spec)
            for expectation in spec.Expectations:
                print(expectation)
                print(expectation.stack)
                print()
            print()
        print()
    
    print("Done")