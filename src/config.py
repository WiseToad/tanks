from typing import Any
from configobj import ConfigObj
from configobj.validate import Validator, ValidateError

class Config(ConfigObj):
    configspec = {
        "server.host": "string(default='localhost')",
        "server.port": "integer(default=5000)",
        "player.name": "string(default='PLAYER')",
    }

    def __init__(self, fileName: str):
        super().__init__(infile=fileName, configspec=self.configspec)
        
        result = self.validate(Validator(), preserve_errors=True)
        if result is not True:
            raise ValidateError("Config file validation failed: " + self.getValidationError(result))

    def getValidationError(self, result: Any, key: str = None) -> str:
        if isinstance(result, dict):
            return next(self.getValidationError(err, key) for key, err in result.items() if err is not True)
        msg = str(result) if result is not False else "Missing section or parameter or unknown error"
        return f"{key}: {msg}" if key else msg
