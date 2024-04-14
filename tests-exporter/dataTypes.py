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
        self.duration = json["duration"] # in milliseconds
        self.properties = json["properties"]
        self.specs = [Spec(spec_json) for spec_json in json["specs"]]
        
    def __str__(self):
        return self.fullName
    

class Spec:
    def __init__(self, json : str|dict):
        if isinstance(json, str):
            json = loads(json)
            
        self.id = json["id"]
        self.description = json["description"]
        self.fullName = json["fullName"]
        self.filename = json["filename"]
        self.Expectations = []
        for expectation in json["failedExpectations"]:
            self.Expectations.append(Expectation.from_json(expectation))
        for expectation in json["passedExpectations"]:
            self.Expectations.append(Expectation.from_json(expectation))
        self.deprecationWarnings = json["deprecationWarnings"]
        self.duration = json["duration"]
        self.properties = json["properties"]
        self.pendingReason = json["pendingReason"]
        self.status = Status(json["status"])
        
    def __str__(self):
        return self.fullName
    

class Expectation:
    def __init__(self, json : str|dict):
        if isinstance(json, str):
            json = loads(json)
            
        self.matcherName = json["matcherName"]
        self.message = json["message"]
        self.stack = Stack(json["stack"])
        self.passed = json["passed"]
        
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
    
    def __str__(self):
        return self.value
    

class Stack:
    class Position:
        def __init__(self, position : str):
            if position == "(<unknown>)":
                self.path = None
                self.line = None
                self.column = None
                return
            
            self.path, self.line, self.column = re.match(r"(.+):(\d+):(\d+)", position).groups()
            self.path = self.path.split('(')[-1]
            
        def __str__(self):
            return f"{self.path}:{self.line}:{self.column}"
    
    
    def __init__(self, string : str):
        self.stack = []
        for line in string.split("\n"):
            line = line.strip()
            if line.count("(") == 1 and line.count(")") == 1:
                self.stack.append(self.Position(line))
            elif line != "":
                self.stack.append(self.Position("(<unknown>)"))
                

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
        self.duration = json["duration"] # in milliseconds
        self.skipped = json["skipped"]
        self.passed = json["passed"]
        assert self.passed == self.specs - self.failures - self.pending - self.skipped # sanity check
        self.startDate = datetime.fromisoformat(json["startDate"])
        self.endDate = self.startDate + timedelta(milliseconds=self.duration)
        
    def __str__(self):
        return f"{self.appName} {self.appVersion} - {self.startDate}"
    
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