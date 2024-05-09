from json5 import loads
import os
import sys
from datetime import datetime, timedelta, timezone
from dataTypes import Suite, Summary, Spec, Status, Stack, PLATFORM, Duration, PlatformData
from utils import *
from typing import Callable
import argparse
from gamuLogger import error, info, warning, debug, critical

OUTPUT_DIR = "reports"

UTC = timezone(timedelta(hours=0)) #UTC

def parse_report(file) -> tuple[Summary, list[Suite], Suite]:
    with open(file, "r") as f:
        data = f.read()
        
    # Try to parse as JSON5

    try:
        data = loads(data)
    except Exception as e:
        error(f"Error parsing JSON5: {e}")
        sys.exit(1)
        
    # data should be a dictionary with at least one key "results", which is another dictionary
    
    if not isinstance(data, dict):
        error("Invalid JSON5 format")
        sys.exit(1)
        
    if "summary" not in data or "suites" not in data:
        error("Invalid JSON5 format")
        sys.exit(1)
        
    summary = Summary(data["summary"])
        
    files = data["files"]
        
    suites = [Suite(suite, files) for suite in data["suites"].values()]
    
    orphans = Suite.suiteForOrphans(data["orphans"], files)
        
    #data is like the file report.json
    return summary, suites, orphans

def build_platform_badge(platform : PLATFORM):
    return load_template("resources/common/platformBadge.template.html",
                        name=platform.name,
                        icon=getIcon(platform.name)
                    )

def build_status_badge(status : Status):
    return load_template("resources/common/statusBadge.template.html",
                        status=status,
                        color=getColorClass(status),
                        icon=getIcon(status.name)
                    )

def build_durations_list(durations : PlatformData):
    durationList = ""
    for platform, duration in durations.items():
        badge = build_platform_badge(platform)
        duration_html = load_template("resources/common/statsList.template.html",
                                platformBadge=badge,
                                data=duration.get()
                            )
        durationList += duration_html
    return durationList

def build_data_list(data : PlatformData):
    dataList = ""
    for platform, value in data.items():
        badge = build_platform_badge(platform)
        data_html = load_template("resources/common/statsList.template.html",
                            platformBadge=badge,
                            data=value
                        )
        dataList += data_html
    return dataList

def build_index(summary : Summary):
    
    platforms = ""
    for platform in summary.platforms:
        platform_html = load_template("resources/index/platformListElement.template.html",
                                name=platform.name,
                                icon=getIcon(platform.name),
                            )
        platforms += platform_html
        
    mainInfo_html = load_template("resources/index/info.template.html",
                            appName=summary.appName,
                            appVersion=summary.appVersion,
                            testDateTime=summary.startDate.strftime("%Y-%m-%d %H:%M:%S %Z"),
                            testDuration=summary.duration.get(),
                            platforms=platforms
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
    
    header = load_template("resources/common/header.template.html", pathToRoot = ".")
    footer = load_template("resources/common/footer.template.html",
                            datetime=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S %Z")
                    )
    
    #load the main template
    mainPage = load_template("resources/common/main.template.html", content=mainPageContent, header=header, footer=footer)

    #export the template to a file
    write_file(OUTPUT_DIR+"/index.html", mainPage)

def build_stack(stack : Stack):
    lastPos = stack.get_last_position()
    context = stack.get_context()
    
    if lastPos is None:
        return ""
    
    lines = ""
    for lineNumber, line in context.items():
        lineNumber = int(lineNumber)
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
                            duration=build_durations_list(suite.duration)
                        )
    
    platforms = PlatformData.getPlatformList()
    passed = suite.passed.getInOrder(platforms)
    failed = suite.failed.getInOrder(platforms)
    pending = suite.pending.getInOrder(platforms)
    skipped = suite.skipped.getInOrder(platforms)
    
    bars = load_template("resources/common/bars.template.html",
                        passed=passed,
                        failed=failed,
                        pending=pending,
                        skipped=skipped,
                        platforms=toJson([str(platform) for platform in platforms]),
                        uid=suite.id
                    )
    
    details = load_template("resources/suites/details.template.html",
                            passed=build_data_list(suite.passed),
                            failed=build_data_list(suite.failed),
                            pending=build_data_list(suite.pending),
                            skipped=build_data_list(suite.skipped),
                            total=len(suite.specs)*len(platforms)
                        )
    
    specs = ""
    for spec in suite.specs:
                
        tabsContent = ""
        for platform in platforms:
            content = ""
            match spec.status[platform]:
                case Status.PASSED:
                    content = "No additional information"
                case Status.FAILED:
                    content = ''.join([build_stack(expect.stack) for expect in spec.expectations[platform] if not expect.passed])
                case Status.PENDING:
                    content = spec.pendingReason
                case Status.SKIPPED:
                    content = "This test was manually skipped"
            
            tab_html = load_template("resources/suites/specs/tabContent.template.html",
                                platform=platform.name,
                                duration=spec.duration[platform].get(),
                                content=content, 
                                checked="checked" if platform == platforms[0] else "",
                                uid=spec.id
                            )
            tabsContent += tab_html
        
        spec_html = load_template("resources/suites/spec.template.html",
                                fullname=spec.fullName,
                                statusBadge=build_status_badge(getStatusTotal(spec.status)),
                                description=spec.description,
                                tabsContent = tabsContent
                                # content=content,
                                # id=spec.id
                            )
        specs += spec_html
    
    suitePage = load_template("resources/suites/page.template.html",
                            mainInfo=suiteInfo,
                            bars=bars,
                            details=details,
                            specList=specs
                        )
    
    header = load_template("resources/common/header.template.html", pathToRoot="..")
    footer = load_template("resources/common/footer.template.html")
    
    #load the main template
    suitePage = load_template("resources/common/main.template.html", content=suitePage, header=header, footer=footer)

    #export the template to a file
    write_file(OUTPUT_DIR+f"/suites/{suite.id}.html", suitePage)
    
def build_suite_list(suites : list[Suite]):
    suiteList = ""
    for suite in suites:
        
        platforms = PlatformData.getPlatformList()
        passed = suite.passed.getInOrder(platforms)
        failed = suite.failed.getInOrder(platforms)
        pending = suite.pending.getInOrder(platforms)
        skipped = suite.skipped.getInOrder(platforms)
        
        bars = load_template("resources/common/bars.template.html",
                            passed=passed,
                            failed=failed,
                            pending=pending,
                            skipped=skipped,
                            platforms=toJson([str(platform) for platform in platforms]),
                            uid=suite.id
                        )
        
        suite_html = load_template("resources/suiteslist/suite.template.html",
                                suiteName=suite.fullName,
                                statusBadge = build_status_badge(getStatusFromSuite(suite)),
                                description=suite.description,
                                fileName=suite.filename,
                                duration=build_durations_list(suite.duration),
                                bars = bars,
                                details=f"suites/{suite.id}.html",
                                pathToRoot=".."
                            )
        suiteList += suite_html
    
    suiteListPage = load_template("resources/suiteslist/page.template.html", suiteList=suiteList)
    
    header = load_template("resources/common/header.template.html", pathToRoot="..")
    footer = load_template("resources/common/footer.template.html",
                        datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
                    )
    #load the main template
    suiteListPage = load_template("resources/common/main.template.html", content=suiteListPage, header=header, footer=footer)

    #export the template to a file
    write_file(OUTPUT_DIR+"/suites/index.html", suiteListPage)
    
def build_spec_inline(spec : Spec):
    spec_html = load_template("resources/specslist/spec.template.html",
                            suite=spec.parentSuite.fullName if spec.parentSuite.id != "orphans" else "",
                            name=spec.fullName,
                            statusBadge=build_status_badge(getStatusTotal(spec.status)),
                            details="suites/" + spec.parentSuite.id + ".html#" + spec.id,
                            pathToRoot=".."
                        )
    return spec_html
    
def build_spec_list(specs : list[Spec]):
    specList = ""
    for spec in specs:
        specList += build_spec_inline(spec)
        
    specListPage = load_template("resources/specslist/page.template.html", specList=specList)
    
    header = load_template("resources/common/header.template.html", pathToRoot="..")
    footer = load_template("resources/common/footer.template.html",
                        datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
                    )
    #load the main template
    specListPage = load_template("resources/common/main.template.html", content=specListPage, header=header, footer=footer)

    #export the template to a file
    write_file(OUTPUT_DIR+"/specs/index.html", specListPage)
    
def build_spec_list_from_suites(suites : list[Suite]):
    specs = []
    for suite in suites:
        specs += suite.specs
        
    build_spec_list(specs)
    
    
    
def main(report_file, output_dir):
        
    global OUTPUT_DIR
    OUTPUT_DIR = output_dir
    clearFolder(OUTPUT_DIR)
        
    if not os.path.os.path.isfile(report_file):
        critical(f"File {report_file} not found")
        sys.exit(1)
        
    summary, suites, orphans = parse_report(report_file)
    
    info("Building index")
    try:
        build_index(summary)
    except Exception as e:
        error("Cannot build index: {e}")
    else:
        debug("Index built")
    
    
    for suite in suites+[orphans]:
        info(f"Building suite {suite.fullName}")
        try:
            build_suite_index(suite)
        except Exception as e:
            error(f"Cannot build suite {suite.fullName}: {e}")
            raise e
        else:
            debug(f"Suite {suite.fullName} built")
        
    info("Building suite list")
    try:
        build_suite_list(suites+[orphans])
    except Exception as e:
        error(f"Cannot build suite list: {e}")
    else:
        debug("Suite list built")
    
    info("Building spec list")
    try:
        build_spec_list_from_suites(suites+[orphans])
    except Exception as e:
        error(f"Cannot build spec list: {e}")
    else:
        debug("Spec list built")
        
    info("Build complete")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate HTML reports from JSON5 reports")
    parser.add_argument("report_file", type=str, help="The JSON5 report file")
    parser.add_argument("-o", "--output", help="The output directory", default="reports")
    args = parser.parse_args()
    
    main(args.report_file, args.output)