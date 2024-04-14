from xml.etree import ElementTree as ET
from json5 import loads
import os
import sys
from datetime import datetime
from dateutil import parser

from dataTypes import Suite, Summary, Spec

def get_duration(durationMs: int) -> str:
    if durationMs < 1000:
        return f"{durationMs} milliseconds"
    seconds = durationMs / 1000
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.2f} minutes"
    hours = minutes / 60
    return f"{hours:.2f} hours"

def load_template(file, **kwargs):
    with open(file, "r") as f:
        template = f.read() #type: str
    for key, value in kwargs.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template

def parse_report(file) -> tuple[Summary, list[Suite], list[Spec]]:
    with open(file, "r") as f:
        data = f.read()
        
    # Try to parse as JSON5

    try:
        data = loads(data)
    except Exception as e:
        print(f"Error parsing JSON5: {e}")
        sys.exit(1)
        
    # data should be a dictionary with at least one key "results", which is another dictionary
    
    if not isinstance(data, dict):
        print("Invalid JSON5 format")
        sys.exit(1)
        
    if "summary" not in data or "suites" not in data:
        print("Invalid JSON5 format")
        sys.exit(1)
        
    suites = [Suite(suite) for suite in data["suites"].values()]
    orphansSpecs = [] #specs that are not part of a suite
    for orphansSpec in data["orphansSpecs"]: #specifications that are not part of a suite	
        orphansSpecs.append(Spec(orphansSpec))
        
        
    #data is like the file report.json
    return Summary(data["summary"]), suites, orphansSpecs


def build_index(summary : Summary, suites : list[Suite], orphansSpecs : list[Spec]):
    
    mainInfo_html = load_template("resources/mainInfo.template.html",
                            appName=summary.appName,
                            appVersion=summary.appVersion,
                            testDateTime=summary.startDate.strftime("%Y-%m-%d %H:%M:%S %Z"),
                            testDuration=get_duration(summary.duration),
                            testCount=summary.specs,
                        )
    
    summary_html = load_template("resources/summary.template.html", 
                            passed=summary.passed,
                            failed=summary.failures,
                            pending=summary.pending,
                            skipped=summary.skipped
                        )
    
    details_html = load_template("resources/details.template.html",
                            passed=summary.passed,
                            failed=summary.failures,
                            pending=summary.pending,
                            skipped=summary.skipped,
                            total=summary.specs
                        )
    
    #load the main page template
    mainPageContent = load_template("resources/mainPage.template.html",
                            mainInfo=mainInfo_html,
                            summary=summary_html,
                            details=details_html
                        )
    
    header = load_template("resources/header.template.html")
    footer = load_template("resources/footer.template.html")
    
    #load the main template
    mainPage = load_template("resources/main.template.html", content=mainPageContent, header=header, footer=footer)

    #export the template to a file
    with open("reports/index.html", "w") as f:
        f.write(mainPage)
    

    
def main(argv):
    if len(argv) < 2:
        print("Usage: python main.py <report-file>")
        sys.exit(1)

    file = argv[1]
    if not os.path.isfile(file):
        print(f"File {file} not found")
        sys.exit(1)
        
    summary, suites, orphansSpecs = parse_report(file)
    build_index(summary, suites, orphansSpecs)
    
if __name__ == "__main__":
    main(sys.argv)