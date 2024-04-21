from json5 import loads, dumps
import os
from datetime import datetime

def fileName(path):
    return os.path.basename(path)

def allEqual(elements : list):
    return all(element == elements[0] for element in elements)

def extractPlatform(data):
    return data['summary']['os']

def error(message : str):
    print(f"\033[91m{message}\033[0m")

def getInputs(inputFolder):
    inputFiles = []
    for dirpath, dirname, filename in os.walk(inputFolder):
        for file in filename:
            if file.endswith("report.json"):
                print(dirpath, file)
                inputFiles.append(os.path.join(dirpath, file))
    return inputFiles


def mergeSummary(summaries):
    print("Merging summaries")
    output = {}
    output["appName"] = summaries[0]["appName"]
    output["appVersion"] = summaries[0]["appVersion"]
    output["platforms"] = [summary["os"] for summary in summaries]
    output["specs"] = sum([summary["specs"] for summary in summaries], 0)
    output["failures"] = sum([summary["failures"] for summary in summaries], 0)
    output["passed"] = sum([summary["passed"] for summary in summaries], 0)
    output["pending"] = sum([summary["pending"] for summary in summaries], 0)
    output["skipped"] = sum([summary["skipped"] for summary in summaries], 0)
    output["duration"] = sum([summary["duration"] for summary in summaries], 0)
    output["startDate"] = min([summary["startDate"] for summary in summaries], key=lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S.%fZ"))
    return output

def mergeSpecs(specs, platforms):
    if len(specs) != len(platforms):
        raise Exception("specs and platforms must have the same length")
    
    output = {}
    # merge common fields
    output["id"] = specs[0]["id"]
    output["description"] = specs[0]["description"]
    output["fullName"] = specs[0]["fullName"]
    output["parentSuiteId"] = specs[0]["parentSuiteId"]
    output["filename"] = specs[0]["filename"]
    output["platforms"] = {}
    
    #merge platform specific fields
    for i in range(len(specs)):
        platform = platforms[i]
        spec = specs[i]
        output["platforms"][platform] = {}
        output["platforms"][platform]["failedExpectations"] = spec["failedExpectations"]
        output["platforms"][platform]["passedExpectations"] = spec["passedExpectations"]
        output["platforms"][platform]["deprecationWarnings"] = spec["deprecationWarnings"]
        output["platforms"][platform]["pendingReason"] = spec["pendingReason"]
        output["platforms"][platform]["duration"] = spec["duration"]
        output["platforms"][platform]["debugLogs"] = spec["debugLogs"]
        output["platforms"][platform]["status"] = spec["status"]
    
    return output

def mergeOrphans(orphans, platforms):
    print("Merging orphans")
    
    output = {}
    
    output["platforms"] = {}
    for i in range(len(orphans)):
        platform = platforms[i]
        orphan = orphans[i]
        output["platforms"][platform] = {}
        output["platforms"][platform]["failed"] = orphan["failed"]
        output["platforms"][platform]["passed"] = orphan["passed"]
        output["platforms"][platform]["pending"] = orphan["pending"]
        output["platforms"][platform]["skipped"] = orphan["skipped"]
        output["platforms"][platform]["duration"] = orphan["duration"]
        output["platforms"][platform]["specs"] = orphan["failed"] + orphan["passed"] + orphan["pending"] + orphan["skipped"]
    
    output["specs"] = {}
    for key in orphans[0]["specs"].keys():
        output["specs"][key] = mergeSpecs([orphan["specs"][key] for orphan in orphans], platforms)
    return output

def mergeSuites(suites, platforms): # suites is the list of the same suite from different platforms
    print("Merging suites")
    
    if not len(suites) == len(platforms):
        raise Exception("suites and platforms must have the same length")
    
    output = {}
    
    # merge common fields
    output["id"] = suites[0]["id"]
    output["description"] = suites[0]["description"]
    output["fullName"] = suites[0]["fullName"]
    output["parentSuiteId"] = suites[0]["parentSuiteId"]
    output["filename"] = fileName(suites[0]["filename"])
    
    # merge specs
    output["specs"] = {}
    for key in suites[0]["specs"].keys():
        output["specs"][key] = mergeSpecs([suite["specs"][key] for suite in suites], platforms)
        
    # merge platform specific fields
    output["platforms"] = {}
    for i in range(len(suites)):
        platform = platforms[i]
        suite = suites[i]
        output["platforms"][platform] = {}
        output["platforms"][platform]["failedExpectations"] = suite["failedExpectations"]
        output["platforms"][platform]["deprecationWarnings"] = suite["deprecationWarnings"]
        output["platforms"][platform]["duration"] = suite["duration"]
        output["platforms"][platform]["passed"] = suite["passed"]
        output["platforms"][platform]["failed"] = suite["failed"]
        output["platforms"][platform]["pending"] = suite["pending"]
        output["platforms"][platform]["skipped"] = suite["skipped"]
        output["platforms"][platform]["status"] = suite["status"]

    
    return output

def mergeAllSuites(suites, platforms):
    output = {}
    for key in suites[0].keys():
        output[key] = mergeSuites([suite[key] for suite in suites], platforms)
    return output

def mergeFiles(files, platforms):
    output = {}
    assert len(files) == len(platforms)
    for i in range(len(files)):
        platform = platforms[i]
        file = files[i]
        output[platform] = file
    return output

def main(argv):
    if len(argv) < 2:
        print("Usage: python main.py <test reports dir> [output file]")
        return
    
    outputfile = "output.json"
    if len(argv) == 3:
        outputfile = argv[2]
    
    inputfiles = getInputs(argv[1])
    if outputfile in inputfiles:
        inputfiles.remove(outputfile)
    if len(inputfiles) == 0:
        print("No input files found")
        return

    inputDatas = []
    for inputfile in inputfiles:
        with open(os.path.join(argv[1], inputfile), "r") as f:
            print(f"Reading {inputfile}")
            inputDatas.append(loads(f.read()))

    platforms = []
    for inputData in inputDatas:
        try:
            platforms.append(extractPlatform(inputData))
        except KeyError:
            error(f"Error: {inputData} is not a valid test report, ignoring it")

    output = {
        "summary": mergeSummary([inputData["summary"] for inputData in inputDatas]),
        "suites": mergeAllSuites([inputData["suites"] for inputData in inputDatas], platforms),
        "orphans": mergeOrphans([inputData["orphans"] for inputData in inputDatas], platforms),
        "files": mergeFiles([inputData["files"] for inputData in inputDatas], platforms)
    }
    
    # write output to file
    with open(outputfile, "w") as f:
        f.write(dumps(output, indent=4, quote_keys=True, trailing_commas=False))


if __name__ == '__main__':
    import sys
    main(sys.argv)