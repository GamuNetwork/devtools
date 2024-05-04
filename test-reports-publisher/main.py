# usage : python main.py <token> <repository> <branch> <test-reports-path>

import os
import sys
import shutil
import argparse

from printer import Printer, deep_debug, debug, info, warning, error, critical, message, COLORS, chrono


from api import API

@chrono
def main(token, repository, branch, test_reports_path, simulate=False, clean=True):
    
    try:
        token = os.environ[token]
        debug(f"GITHUB_TOKEN found in environment variables")
    except KeyError:
        critical(f"Environment variable {token} not found")
        return
    
    Printer.add_sensitive(token)
    if simulate:
        message("Simulation mode is enabled, no changes will be made to the distant repository", COLORS.YELLOW)
    try:
        with API(token, 'gamunetwork/gamunetwork.github.io', simulate=simulate) as (api, path):
            api.auto_clean = clean
            reports_path = f"{path}/docs/reports/{repository}/{branch}"
            if os.path.exists(reports_path):
                shutil.rmtree(reports_path)
            os.makedirs(reports_path, exist_ok=True)
            
            shutil.copytree(test_reports_path, reports_path, dirs_exist_ok=True)
            info(f"Test reports copied to {reports_path}")
            
            api.push(f"Updated test reports for {repository}/{branch}")
    except Exception as e:
        critical(str(e))
        sys.exit(1)
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Push test reports to repository')
    parser.add_argument('tokenVarName', help='GitHub api token environment variable name')
    parser.add_argument('repository', help='Repository name')
    parser.add_argument('branch', help='Branch name')
    parser.add_argument('test_reports_path', help='Test reports path')
    parser.add_argument('-s', '--simulate', action='store_true', help='simulate the process without pushing to repository')
    parser.add_argument('-nc', '--no-clean', action='store_true', help='do not delete the cloned repository after the process is done')
    
    debug_group = parser.add_argument_group('Debugging options (use only one of them)')
    debug_group = debug_group.add_mutually_exclusive_group()
    debug_group.add_argument('-d', '--debug', action='store_true', help='enable debug mode (show debug messages)')
    debug_group.add_argument('-dd', '--deep-debug', action='store_true', help='enable deep debug mode (show deep debug messages)')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='enable quiet mode (show only error messages)')

    args = parser.parse_args()
    
    if args.debug:
        Printer().set_level(Printer.LEVELS.DEBUG)
    elif args.deep_debug:
        Printer().set_level(Printer.LEVELS.DEEP_DEBUG)
    elif args.quiet:
        Printer().set_level(Printer.LEVELS.ERROR)
    
    
    main(args.tokenVarName, args.repository, args.branch, args.test_reports_path, args.simulate, not args.no_clean)