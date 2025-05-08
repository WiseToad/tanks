from typing import Any
import yaml

class Config:
    __data: dict[str, Any]

    def __init__(self, fileName: str = None):
        self.__data = {}
        if fileName is not None:
            self.load(fileName)

    def load(self, fileName: str):
        self.__data = {}
        try:
            with open(fileName, "r") as f:
                self.__data = yaml.safe_load(f)
            if self.__data is None:
                self.__data = {}
        except FileNotFoundError:
            pass

    def save(self, fileName: str):
        with open(fileName, "w", encoding="utf8") as f:
            yaml.safe_dump(self.__data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    def get(self, key: str, default: Any = None) -> Any:
        return self.__data.get(key, default)

    def put(self, key: str, value: Any):
        self.__data[key] = value
