from typing import Any
from ruamel.yaml import YAML

class Config:
    def __init__(self, fileName: str = None):
        self.data = {}
        if fileName is not None:
            self.load(fileName)

    def load(self, fileName: str):
        yaml = YAML()
        self.data = {}
        try:
            with open(fileName, "r", encoding="utf8") as f:
                self.data = yaml.load(f)
            if self.data is None:
                self.data = {}
        except FileNotFoundError:
            pass

    def save(self, fileName: str):
        yaml = YAML()
        with open(fileName, "w", encoding="utf8", newline="\n") as f:
            yaml.dump(self.data, f)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def put(self, key: str, value: Any):
        self.data[key] = value
