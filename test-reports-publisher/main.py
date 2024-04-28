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
        
    def _download_file(self, url, path):
        response = requests.get(url)
        response.raise_for_status()
        content = response.json()['content']
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(content))
        
    def _download_dir(self, url, path):
        response = requests.get(url)
        response.raise_for_status()
        tree = response.json()['tree']
        for item in tree:
            if item['type'] == 'blob':
                self._download_file(item['url'], f'{path}/{item["path"]}')
            else:
                self._download_dir(item['url'], f'{path}/{item["path"]}')
        
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
                self._download_file(item['url'], f'{self.path()}/{item["path"]}')
            else:
                self._download_dir(item['url'], f'{self.path()}/{item["path"]}')
            
        print('Done', flush=True)
    
    def _create_blob(self, content) -> Blob_sha:
        url = f'{self.repository_url}/git/blobs'
        content64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        response = requests.post(url, headers=self.headers, json={'content': content64, 'encoding': 'utf-8'})
        response.raise_for_status()
        return response.json()['sha']
    
    def _create_tree(self, fileTree) -> Tree_sha:
        url = f'{self.repository_url}/git/trees'
        tree = []
        for file in fileTree["files"]:
            tree.append({
                'path': file,
                'mode': '100644',
                'type': 'blob',
                'sha': self._create_blob(file)
            })
        for dir in fileTree["dirs"]:
            tree.append({
                'path': dir,
                'mode': '040000',
                'type': 'tree',
                'sha': self._create_tree(dir)
            })
        response = requests.post(url, headers=self.headers, json={'tree': tree})
        response.raise_for_status()
        return response.json()['sha']
    
    def _get_commit_sha(self) -> Commit_sha:
        url = f'{self.repository_url}/git/refs/heads/{self.branch}'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()['object']['sha']
    
    def _create_commit(self, message, tree_sha) -> Commit_sha:
        url = f'{self.repository_url}/git/commits'
        response = requests.post(url, headers=self.headers, json={
            'message': message,
            'tree': tree_sha,
            'parents': [self._get_commit_sha()]
        })
        response.raise_for_status()
        return response.json()['sha']
    
    def _update_ref(self, commit_sha):
        url = f'{self.repository_url}/git/refs/heads/{self.branch}'
        response = requests.patch(url, headers=self.headers, json={'sha': commit_sha})
        response.raise_for_status()

    def push(self, message):
        tree = self._build_fileTree()

        print(f"Committing changes in {self.repository} ...", flush=True)
        
        tree_sha = self._create_tree(tree)
        commit_sha = self._create_commit(message, tree_sha)
        self._update_ref(commit_sha)
        
        print('Done', flush=True)
        
    def _build_fileTree(self):
        return self._recurse_build_fileTree(self.path())
        
    def _recurse_build_fileTree(self, path):
        fileTree = {"files": [], "dirs": []}
        for filepath in os.listdir(path):
            if os.path.isfile(filepath):
                fileTree["files"].append(filepath)
            else:
                fileTree["dirs"].append(self._recurse_build_fileTree(filepath))
        return fileTree
    
    def clean(self):
        print('Cleaning up ...')
        cwd = os.getcwd()
        name = self.repository.split('/')[-1]
        os.system(f'rm -rf {name}')
        print(f'Directory {name} removed')
        
    def __enter__(self):
        self.auto_clean = True
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.auto_clean:
            self.clean()
        
    def path(self):
        return self._path

with API(TOKEN, 'gamunetwork/gamunetwork.github.io') as api:
    api.auto_clean = False
    api.clone()
    
    path = api.path()
    with open(f'{path}/docs/test.html', 'w', encoding='utf-8') as f:
        f.write('<h1>Hello from GamuNetwork auto script</h1>')
    with open(f'{path}/docs/index.html', 'r', encoding='utf-8') as f:
        print(f.read())
    
    api.push('Updating files')