import requests
import os
import base64

type Commit_sha = str
type Tree_sha = str
type Blob_sha = str

class API:
    def __init__(self, token, repository, branch='main'):
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json'
        }
        self.base_url = 'https://api.github.com'
        self.repository_url = f'{self.base_url}/repos/{repository}'
        self.repository = repository
        self.branch = branch
        
        cwd = os.getcwd()
        name = self.repository.split('/')[-1]
        
        self._path = f'{cwd}/{name}'
        
    def abs(self, path):
        return f'{self._path}/{path}'
        
    def __download_file(self, url, path):
        response = requests.get(url)
        response.raise_for_status()
        content = response.json()['content']
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(content))
        
    def __download_dir(self, url, path):
        response = requests.get(url)
        response.raise_for_status()
        tree = response.json()['tree']
        for item in tree:
            if item['type'] == 'blob':
                self.__download_file(item['url'], f'{path}/{item["path"]}')
            else:
                self.__download_dir(item['url'], f'{path}/{item["path"]}')
        
    def clone(self):
        cwd = os.getcwd()
        name = self.repository.split('/')[-1]
        
        if os.path.exists(name):
            print(f"Directory {name} already exists")
            return
        
        os.mkdir(name)
        
        url = f'{self.repository_url}/git/refs/heads/{self.branch}'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        sha = response.json()['object']['sha']
        
        url = f'{self.repository_url}/git/trees/{sha}'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        tree = response.json()['tree']
        
        print(f"Cloning {self.repository} into {self.path()} ...", flush=True)
        
        for item in tree:
            if item['type'] == 'blob':
                self.__download_file(item['url'], f'{self.path()}/{item["path"]}')
            else:
                self.__download_dir(item['url'], f'{self.path()}/{item["path"]}')
            
        print('Done', flush=True)
    
    def __create_blob(self, filepath) -> Blob_sha:
        url = f'{self.repository_url}/git/blobs'
        
        content = open(filepath, 'r', encoding='utf-8').read()
        
        content64 = base64.b64encode(content.encode()).decode()
        response = requests.post(url, headers=self.headers, json={'content': content64, 'encoding': 'base64'})
        response.raise_for_status()
        return response.json()['sha']
    
    def getRelPath(self, path):
        return path.replace(self.path() + "/", "")
    
    def _fake_create_tree(self, fileTree) -> None:
        tree = []
        for file in fileTree["files"]:
            path = self.getRelPath(file)
            filename = os.path.basename(path)
            print(f"Adding {path} to tree...", flush=True)
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
                'sha': self._fake_create_tree(dir)
            })
        print({'tree': tree})
    
    def __create_tree(self, fileTree) -> Tree_sha:
        url = f'{self.repository_url}/git/trees'
        tree = []
        for file in fileTree["files"]:
            path = self.getRelPath(file)
            filename = os.path.basename(path)
            print(f"Adding {path} to tree...", flush=True)
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
        response = requests.post(url, headers=self.headers, json={'tree': tree})
        response.raise_for_status()
        return response.json()['sha']
    
    def __get_commit_sha(self) -> Commit_sha:
        url = f'{self.repository_url}/git/refs/heads/{self.branch}'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()['object']['sha']
    
    def __create_commit(self, message, tree_sha) -> Commit_sha:
        url = f'{self.repository_url}/git/commits'
        response = requests.post(url, headers=self.headers, json={
            'message': message,
            'tree': tree_sha,
            'parents': [self.__get_commit_sha()]
        })
        response.raise_for_status()
        return response.json()['sha']
    
    def __update_ref(self, commit_sha):
        url = f'{self.repository_url}/git/refs/heads/{self.branch}'
        response = requests.patch(url, headers=self.headers, json={'sha': commit_sha})
        response.raise_for_status()

    def fake_push(self, message):
        tree = self.__build_fileTree()

        print(f"Committing changes in {self.repository} ...", flush=True)
        
        self._fake_create_tree(tree)
        
        print('Done', flush=True)

    def push(self, message):
        tree = self.__build_fileTree()

        print(f"Committing changes in {self.repository} ...", flush=True)
        
        tree_sha = self.__create_tree(tree)
        commit_sha = self.__create_commit(message, tree_sha)
        self.__update_ref(commit_sha)
        
        print('Done', flush=True)
        
    def __build_fileTree(self):
        return self.__recurse_build_fileTree(self.path())
        
    def __recurse_build_fileTree(self, path):
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
        return fileTree
    
    def clean(self):
        print('Cleaning up ...')
        cwd = os.getcwd()
        name = self.repository.split('/')[-1]
        os.system(f'rm -rf {name}')
        print(f'Directory {name} removed')
        
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
        self.clone()
        return self, self.path()
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.auto_clean:
            self.clean()
        
    def path(self):
        return self._path
