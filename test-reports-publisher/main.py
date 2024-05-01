# usage : python main.py <token> <repository> <branch> <test-reports-path>

import os
import sys
import shutil

from api import API

def main(argv):
    token = argv[1]
    repository = argv[2]
    branch = argv[3]
    test_reports_path = argv[4]
    
    with API(token, 'gamunetwork/gamunetwork.github.io') as (api, path):
        reports_path = f"{path}/docs/reports/{repository}/{branch}"
        if os.path.exists(reports_path):
            shutil.rmtree(reports_path)
        os.makedirs(reports_path, exist_ok=True)
        
        shutil.copytree(test_reports_path, reports_path, dirs_exist_ok=True)
        print(f"Test reports copied to {reports_path}")
        
        api.push(f"Updated test reports for {repository}/{branch}")
        print("Test reports pushed to repository")
        
if __name__ == '__main__':
    argv = sys.argv
    if len(argv) != 5:
        print("Usage: python main.py <token> <repository> <branch> <test-reports-path>")
        sys.exit(1)
    main(argv)