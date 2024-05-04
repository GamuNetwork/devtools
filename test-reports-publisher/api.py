import requests
import os
import base64

from printer import Printer, deep_debug, debug, info, warning, error, critical, deep_debug_func, debug_func

type Commit_sha = str
type Tree_sha = str
type Blob_sha = str

class RequestError(Exception):
    def __init__(self, code, message):
        
        msg = ""
        
        if(code == 400):
            msg = "Bad Request: Invalid request"
        elif(code == 401):
            msg = "Unauthorized: Invalid token"
        elif(code == 402):
            msg = "Payment Required: Rate limit exceeded"
        elif(code == 403):
            msg = "Forbidden: Insufficient permissions"
        elif(code == 404):
            msg = "Not Found: Repository not found"
        elif(code == 405):
            msg = "Method Not Allowed: Invalid method"
        elif(code == 406):
            msg = "Not Acceptable: Invalid Accept header"
        elif(code == 422):
            msg = "Unprocessable Entity: Invalid request"
        elif(code == 429):
            msg = "Too Many Requests: Rate limit exceeded"
            
        elif(code == 500):
            msg = "Internal Server Error: Server error"
        elif(code == 501):
            msg = "Not Implemented: Invalid request"
        elif(code == 502):
            msg = "Bad Gateway: Server error"
        elif(code == 503):
            msg = "Service Unavailable: Server error"
        elif(code == 504):
            msg = "Gateway Timeout: Server error"
        elif(code == 505):
            msg = "HTTP Version Not Supported: Invalid request"
        elif(code == 506):
            msg = "Variant Also Negotiates: Invalid request"
        elif(code == 507):
            msg = "Insufficient Storage: Server error"
        elif(code == 508):
            msg = "Loop Detected: Server error"
        elif(code == 510):
            msg = "Not Extended: Invalid request"
        elif(code == 511):
            msg = "Network Authentication Required: Invalid request"
        else:
            msg = "Unknown Error"
    
        super().__init__(f"Error {code}: {msg} - {message}")
        
    @staticmethod
    def from_response(response):
        """Raise a RequestError from a response object if the status code is not 200."""
        if response.status_code < 200 or response.status_code >= 300:
            raise RequestError(response.status_code, response.json()['message'])

class API:
    def __init__(self, token, repository, branch='main', simulate=False):
        self.simulate = simulate
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json'
        }
        debug(f'API headers: {self.headers}')
        self.base_url = 'https://api.github.com'
        self.repository_url = f'{self.base_url}/repos/{repository}'
        self.repository = repository
        self.branch = branch
        
        debug(f'Repository URL: {self.repository_url}')
        
        cwd = os.getcwd()
        debug(f'Current working directory: {cwd}')
        
        name = self.repository.split('/')[-1]
        self._path = f'{cwd}/{name}'
        
        debug(f'Path: {self._path}')
        
    def abs(self, path):
        return f'{self._path}/{path}'
        
    def __get(self, url):
        deep_debug(f'GET {url}')
        response = requests.get(url, headers=self.headers)
        deep_debug(f'Response: {response.status_code}\n response keys: {response.json().keys()}')
        RequestError.from_response(response)
        return response.json()

    def __post(self, url, data):
        deep_debug(f'POST {url}\n{data if len(str(data)) < 200 else "data too long to be displayed"}')
        response = requests.post(url, headers=self.headers, json=data)
        deep_debug(f'Response: {response.status_code}\n response keys: {response.json().keys()}')
        RequestError.from_response(response)
        return response.json()
        
    def __download_file(self, url, path):
        debug(f'Downloading {path} ...')
        content = self.__get(url)['content']
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(content))
        debug('Downloaded')
        
    def __download_dir(self, url, path):
        tree = self.__get(url)['tree']
        for item in tree:
            if item['type'] == 'blob':
                self.__download_file(item['url'], f'{path}/{item["path"]}')
            else:
                self.__download_dir(item['url'], f'{path}/{item["path"]}')
        
    def clone(self) -> bool:
        info(f"Looking for cloning {self.repository} ...")
        cwd = os.getcwd()
        name = self.repository.split('/')[-1]
        
        if os.path.exists(name):
            error(f"Directory {name} already exists")
            return False
        
        os.mkdir(name)
        
        url = f'{self.repository_url}/git/refs/heads/{self.branch}'
        sha = self.__get(url)['object']['sha']
        
        url = f'{self.repository_url}/git/trees/{sha}'
        tree = self.__get(url)['tree']
        
        info(f"Cloning {self.repository}:{self.branch} into {self.path()} ...")
        
        for item in tree:
            if item['type'] == 'blob':
                self.__download_file(item['url'], f'{self.path()}/{item["path"]}')
            else:
                self.__download_dir(item['url'], f'{self.path()}/{item["path"]}')
            
        info('Repository cloned')
        return True
    
    def __create_blob(self, filepath) -> Blob_sha:
        deep_debug(f'Creating blob for {filepath} ...')
        url = f'{self.repository_url}/git/blobs'
        
        content = open(filepath, 'r', encoding='utf-8').read()
        content64 = base64.b64encode(content.encode()).decode()
        result = self.__post(url, {'content': content64, 'encoding': 'base64'})['sha']
        deep_debug(f'Blob created: {result}')
        return result
    
    def getRelPath(self, path):
        return path.replace(self.path() + "/", "")
    
    def __create_tree(self, fileTree) -> Tree_sha:
        tree = []
        for file in fileTree["files"]:
            path = self.getRelPath(file)
            filename = os.path.basename(path)
            debug(f"Adding {path} to tree...")
            tree.append({
                'path': filename,
                'mode': '100644',
                'type': 'blob',
                'sha': self.__create_blob(file)
            })
        for dir in fileTree["dirs"]:
            tree.append({
                'path': dir["name"],
                'mode': '040000',
                'type': 'tree',
                'sha': self.__create_tree(dir)
            })
            
        if self.simulate:
            debug('Simulation mode enabled; skipping tree creation on GitHub')
            info("created tree :\n"+str(tree))
        return self.__post(f'{self.repository_url}/git/trees', {'tree': tree})['sha']
    
    @deep_debug_func
    def __get_commit_sha(self) -> Commit_sha:
        return self.__get(f'{self.repository_url}/git/refs/heads/{self.branch}')['object']['sha']
    
    @deep_debug_func
    def __create_commit(self, message, tree_sha) -> Commit_sha:
        json={
            'message': message,
            'tree': tree_sha,
            'parents': [self.__get_commit_sha()]
        }
        return self.__post(f'{self.repository_url}/git/commits', json)['sha']
    
    @deep_debug_func
    def __update_ref(self, commit_sha):
        url = f'{self.repository_url}/git/refs/heads/{self.branch}'
        self.__post(url, {'sha': commit_sha})

    def push(self, message):
        info(f"Pushing changes to {self.repository} in {self.branch} ...")
        tree = self.__build_fileTree()

        debug(f"Committing changes in {self.repository} ...")
        
        tree_sha = self.__create_tree(tree)
        if self.simulate:
            debug('Simulation mode enabled; skipping commit creation and ref update on GitHub')
        else:
            commit_sha = self.__create_commit(message, tree_sha)
            self.__update_ref(commit_sha)
        
        info('Changes pushed')
        
    def __build_fileTree(self):
        return self.__recurse_build_fileTree(self.path())
    
    def __recurse_build_fileTree(self, path):
        deep_debug(f"Building file tree for {path} ...")
        fileTree = {"files": [], "dirs": []}
        for filepath in os.listdir(path):
            fullpath = f'{path}/{filepath}'
            if os.path.isfile(fullpath):
                fileTree["files"].append(fullpath)
            else:
                fileTree["dirs"].append({
                    "name": filepath,
                    "files": self.__recurse_build_fileTree(fullpath)["files"],
                    "dirs": self.__recurse_build_fileTree(fullpath)["dirs"]
                })
        deep_debug(f"File tree for {path} built")
        return fileTree
    
    def clean(self):
        debug('Cleaning up ...')
        cwd = os.getcwd()
        name = self.repository.split('/')[-1]
        os.system(f'rm -rf {name}')
        info(f'Directory {name} removed')
    
    def __enter__(self):
        """Usage:\n
        ```
        with API(token, 'gamunetwork/gamunetwork.github.io') as (api, path):
            # modify files in path
            with open(f'{path}/path/to/file', 'w', encoding='utf-8') as f:
                f.write('Hello World!')
            
            # push changes
            api.push('Updating files')
        ```"""
        self.auto_clean = True
        debug('auto clean enabled; use `api.auto_clean = False` to disable')
        if not self.clone():
            raise Exception(f"Failed to clone repository {self.repository}")
        return self, self.path()
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.auto_clean:
            self.clean()
        else:
            warning(f'auto clean disabled; the folder {self.path()} was not removed')
    
    def path(self):
        return self._path
