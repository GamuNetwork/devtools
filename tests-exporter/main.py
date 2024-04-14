from xml.etree import ElementTree as ET
from json5 import loads
import os
import sys
from datetime import datetime
from dateutil import parser

from dataTypes import Suite

def parse_UTCDate(utcDate: str) -> str:
    # utcDate example : "Sun, 14 Apr 2024 17:06:15 GMT"
    dt = parser.parse(utcDate)
    return dt.strftime('%x %X GMT')


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

def parse_report(file) -> dict:
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
        
    #data is like the file report.json
    return data


def build_html(data : dict):
    
    summary = load_template("resources/summary.template.html", 
                            
                        )
    
    mainInfo = load_template("resources/mainInfo.template.html",
                            appName=data["summary"]["appName"],
                            appVersion=data["summary"]["appVersion"],
                            testDateTime=parse_UTCDate(data["summary"]["startDate"]),
                            testDuration=get_duration(data["summary"]["duration"]),
                            testCount=data["summary"]["specs"],
                        )
    
    #load the main page template
    mainPageContent = load_template("resources/mainPage.template.html",
                            summary=summary,
                            mainInfo=mainInfo
                        )
    
    header = load_template("resources/header.template.html")
    
    #load the main template
    mainPage = load_template("resources/main.template.html", content=mainPageContent, header=header)

    
    
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
        
    data = parse_report(file)
    build_html(data)
    
if __name__ == "__main__":
    main(sys.argv)