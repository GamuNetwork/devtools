from xml.etree import ElementTree as ET
from json5 import loads
import os
import sys
from datetime import datetime, timedelta, timezone
from dateutil import parser

from dataTypes import Suite, Summary, Spec, Status, Stack

OUTPUT_DIR = "reports"

TIMEZONE = timezone(timedelta(hours=0))

def load_template(file, **kwargs):
    with open(file, "r") as f:
        template = f.read() #type: str
    for key, value in kwargs.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template

def parse_report(file) -> tuple[Summary, list[Suite], Suite]:
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
    
    orphans = Suite.suiteForOrphans(data["orphans"])
        
    #data is like the file report.json
    return Summary(data["summary"]), suites, orphans

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

def write_file(file, content):
    file = os.path.join(OUTPUT_DIR, file)
    if not os.path.exists(os.path.dirname(file)):
        os.makedirs(os.path.dirname(file))
    with open(file, "w") as f:
        f.write(content)



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
                            skipped=summary.skipped,
                            uid="summary"
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
    footer = load_template("resources/common/footer.template.html",
                            #datetime now in UTC
                            datetime=datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %Z")
                    )
    
    #load the main template
    mainPage = load_template("resources/common/main.template.html", content=mainPageContent, header=header, footer=footer)

    #export the template to a file
    write_file("index.html", mainPage)

def build_stack(stack : Stack):
    lastPos = stack.get_last_position()
    context = stack.get_context()
    
    lines = ""
    for lineNumber, line in context:
        line_html = load_template("resources/suites/stack/line.template.html",
                                lineNumber=lineNumber,
                                line=line,
                                lineClasses="bg-base-content text-accent-content" if lineNumber == lastPos.line else ""
                            )
        lines += line_html
        
    stack_html = load_template("resources/suites/stack.template.html",
                            lines=lines,
                            filename=lastPos.path,
                        )
    return stack_html

def build_suite_index(suite : Suite):
    
    suiteInfo = load_template("resources/suites/info.template.html",
                            name=suite.fullName,
                            description=suite.description,
                            filename=suite.filename,
                            duration=suite.duration.get()
                        )
    
    pie = load_template("resources/common/pie.template.html",
                            passed=suite.passed,
                            failed=suite.failed,
                            pending=suite.pending,
                            skipped=suite.skipped,
                            uid=suite.id
                        )
    
    details = load_template("resources/suites/details.template.html",
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
        
        spec_html = load_template("resources/suites/spec.template.html",
                                fullname=spec.fullName,
                                status=spec.status,
                                colorClass=getColorClass(spec.status),
                                description=spec.description,
                                content=content,
                                id=spec.id
                            )
        specs += spec_html
    
    suitePage = load_template("resources/suites/page.template.html",
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
    write_file(f"suites/{suite.id}.html", suitePage)
    
def build_suite_list(suites : list[Suite]):
    suiteList = ""
    for suite in suites:
        
        pie = load_template("resources/common/pie.template.html",
                            passed=suite.passed,
                            failed=suite.failed,
                            pending=suite.pending,
                            skipped=suite.skipped,
                            uid=suite.id
                        )
        
        suite_html = load_template("resources/suiteslist/suite.template.html",
                                suiteName=suite.fullName,
                                description=suite.description,
                                fileName=suite.filename,
                                duration=suite.duration.get(),
                                pie=pie,
                                details=f"/suites/{suite.id}.html"
                            )
        suiteList += suite_html
    
    suiteListPage = load_template("resources/suiteslist/page.template.html", suiteList=suiteList)
    
    header = load_template("resources/common/header.template.html")
    footer = load_template("resources/common/footer.template.html",
                        datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
                    )
    #load the main template
    suiteListPage = load_template("resources/common/main.template.html", content=suiteListPage, header=header, footer=footer)

    #export the template to a file
    write_file("suites/index.html", suiteListPage)
    
def build_spec_inline(spec : Spec):
    spec_html = load_template("resources/specslist/spec.template.html",
                            suite=spec.parentSuite.fullName,
                            name=spec.fullName,
                            status=spec.status,
                            statusColorClass=getColorClass(spec.status),
                            details="/suites/" + spec.parentSuite.id + ".html#" + spec.id
                        )
    return spec_html
    
def build_spec_list(specs : list[Spec]):
    specList = ""
    for spec in specs:
        specList += build_spec_inline(spec)
        
    specListPage = load_template("resources/specslist/page.template.html", specList=specList)
    
    header = load_template("resources/common/header.template.html")
    footer = load_template("resources/common/footer.template.html",
                        datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
                    )
    #load the main template
    specListPage = load_template("resources/common/main.template.html", content=specListPage, header=header, footer=footer)

    #export the template to a file
    write_file("specs/index.html", specListPage)
    
def build_spec_list_from_suites(suites : list[Suite]):
    specs = []
    for suite in suites:
        specs += suite.specs
        
    build_spec_list(specs)
    
def main(argv):
    if len(argv) < 2:
        print("Usage: python main.py <report-file>")
        sys.exit(1)

    file = argv[1]
    if not os.path.isfile(file):
        print(f"File {file} not found")
        sys.exit(1)
        
    summary, suites, orphans = parse_report(file)
    build_index(summary)
    
    for suite in suites+[orphans]:
        build_suite_index(suite)
        
    build_suite_list(suites+[orphans])
    build_spec_list_from_suites([orphans]+suites)
    
if __name__ == "__main__":
    main(sys.argv)