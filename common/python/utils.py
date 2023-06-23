#   ver:    1.0
#   date:   27/01/2023
#   author: georgiana-bud

"""
Minimalistic implementation of platform's utils
"""
import os
import yaml
 
from typing import Tuple, Callable

from common.python.error import DopError
from common.python.config_utils import ConfigUtils 


class DopUtils:

    @staticmethod
    def config_to_dict(connstring: str) -> Tuple[DopError,dict]:
        return ConfigUtils.config_to_dict(connstring)

    @staticmethod
    def config_get_string(config: dict, keys: list, default_value: str) -> Tuple[bool, str]:
        return ConfigUtils.config_get_string(config, keys, default_value)
        
    @staticmethod
    def config_get_int(config: dict, keys: str, default_value: int) -> Tuple[bool, int]:
        return ConfigUtils.config_get_int(config, keys, default_value)


    @staticmethod
    def parse_yaml_configuration(confile: str) -> Tuple[DopError,dict]:
        conf: dict = {}
        #   check if file exists
        if os.path.exists(confile) == False:
            return (DopError(101,'Configuration file does not exist'), conf)

        with open(confile,'r') as stream:
            try:
                conf = yaml.safe_load(stream)
                return (DopError(),conf)
            except yaml.YAMLError as exc:
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    msg =  f"Error in parsing configuration file: position ({(mark.line+1)}:{(mark.column+1)})"
                    return (DopError(103,msg),conf)
                return(DopError(3,"conf file parsing error"),{})
