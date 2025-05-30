from configobj import ConfigObj
from configobj.validate import Validator, ValidateError

class Config(ConfigObj):
    configspec = {
        "server.host": "string",
        "server.port": "integer",
        "player.name": "string",
    }

    def __init__(self, fileName: str):
        super().__init__(infile=fileName, configspec=self.configspec)
        if self.validate(Validator()) != True:
            raise ValidateError("Invalid config file")
