from xml.etree import ElementTree as ET
from json5 import loads
import os
import sys
from datetime import datetime
from dateutil import parser

from dataTypes import Suite, Summary, Spec, Status, Stack

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
    
    #TODO: handle orphansSpecs (as a suite with no name)
        
        
    #data is like the file report.json
    return Summary(data["summary"]), suites

def getColorClass(status : Status) -> str:
    match status:
        case Status.PASSED:
            return "success"
        case Status.FAILED:
            return "error"
        case Status.PENDING:
            return "warning"
        case Status.SKIPPED:
            return "info"
        case _:
            return "secondary"

def build_index(summary : Summary):
    
    mainInfo_html = load_template("resources/index/info.template.html",
                            appName=summary.appName,
                            appVersion=summary.appVersion,
                            testDateTime=summary.startDate.strftime("%Y-%m-%d %H:%M:%S %Z"),
                            testDuration=summary.duration.get()
                        )
    
    summary_html = load_template("resources/common/pie.template.html", 
                            passed=summary.passed,
                            failed=summary.failures,
                            pending=summary.pending,
                            skipped=summary.skipped
                        )
    
    details_html = load_template("resources/index/details.template.html",
                            passed=summary.passed,
                            failed=summary.failures,
                            pending=summary.pending,
                            skipped=summary.skipped,
                            total=summary.specs
                        )
    
    #load the main page template
    mainPageContent = load_template("resources/index/page.template.html",
                            mainInfo=mainInfo_html,
                            summary=summary_html,
                            details=details_html
                        )
    
    header = load_template("resources/common/header.template.html")
    footer = load_template("resources/common/footer.template.html")
    
    #load the main template
    mainPage = load_template("resources/common/main.template.html", content=mainPageContent, header=header, footer=footer)

    #export the template to a file
    with open("reports/index.html", "w") as f:
        f.write(mainPage)


def build_stack(stack : Stack):
    lastPos = stack.get_last_position()
    context = stack.get_context()
    
    lines = ""
    for lineNumber, line in context:
        line_html = load_template("resources/suite/stack/line.template.html",
                                lineNumber=lineNumber,
                                line=line,
                                lineClasses="bg-base-content text-accent-content" if lineNumber == lastPos.line else ""
                            )
        lines += line_html
        
    stack_html = load_template("resources/suite/stack.template.html",
                            lines=lines,
                            filename=lastPos.path,
                        )
    return stack_html


def build_suite_index(suite : Suite):
    
    suiteInfo = load_template("resources/suite/info.template.html",
                            name=suite.fullName,
                            description=suite.description,
                            filename=suite.filename,
                            duration=suite.duration.get()
                        )
    
    pie = load_template("resources/common/pie.template.html",
                            passed=suite.passed,
                            failed=suite.failed,
                            pending=suite.pending,
                            skipped=suite.skipped
                        )
    
    details = load_template("resources/suite/details.template.html",
                            passed=suite.passed,
                            failed=suite.failed,
                            pending=suite.pending,
                            skipped=suite.skipped,
                            total=len(suite.specs)
                        )
    
    specs = ""
    for spec in suite.specs:
        content = ""
        match spec.status:
            case Status.PASSED:
                content = "No additional information"
            case Status.FAILED:
                content = ''.join([build_stack(expect.stack) for expect in spec.expectations if not expect.passed])
            case Status.PENDING:
                content = spec.pendingReason
            case Status.SKIPPED:
                content = "This test was manually skipped"
        
        spec_html = load_template("resources/suite/spec.template.html",
                                fullname=spec.fullName,
                                status=spec.status,
                                colorClass=getColorClass(spec.status),
                                description=spec.description,
                                content=content
                            )
        specs += spec_html
    
    suitePage = load_template("resources/suite/page.template.html",
                            mainInfo=suiteInfo,
                            pie=pie,
                            details=details,
                            specList=specs,
                            duration=suite.duration.get()
                        )
    
    header = load_template("resources/common/header.template.html")
    footer = load_template("resources/common/footer.template.html")
    
    #load the main template
    suitePage = load_template("resources/common/main.template.html", content=suitePage, header=header, footer=footer)

    #export the template to a file
    with open(f"reports/{suite.id}.html", "w") as f:
        f.write(suitePage)
    
def main(argv):
    if len(argv) < 2:
        print("Usage: python main.py <report-file>")
        sys.exit(1)

    file = argv[1]
    if not os.path.isfile(file):
        print(f"File {file} not found")
        sys.exit(1)
        
    summary, suites = parse_report(file)
    build_index(summary)
    
    for suite in suites:
        build_suite_index(suite)
    
if __name__ == "__main__":
    main(sys.argv)