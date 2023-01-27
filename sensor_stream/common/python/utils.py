#   ver:    1.0
#   date:   27/01/2023
#   author: georgiana-bud

"""
Minimalistic implementation of platform's utils
"""
import base64
import sys
import os
import yaml
import importlib
import importlib.util
import traceback
from uuid import UUID 

from importlib.machinery import SourceFileLoader


from typing import Tuple, Callable

from common.python.error import DopError

import datetime
import hashlib 
import time
from functools import wraps
import binascii


class DopUtils:

    @staticmethod
    def config_to_dict(connstring: str) -> Tuple[DopError,dict]:
        if connstring == "":
            return(DopError(),{})

        conf: dict = {}
        d_conn: list = connstring.split(';')
        for d_conn_item in d_conn:
            if len(d_conn_item) > 0:
                d_item = d_conn_item.split('=')
                conf.update({d_item[0].strip():d_item[1].strip()})
        return (DopError(),conf)

    @staticmethod
    def config_get_string(config: dict, keys: list, default_value: str) -> Tuple[bool, str]:
        for k in keys:            
            if k in config:
                return True, config[k]
        if default_value == None:
            return False, default_value
        return True, default_value
        
    @staticmethod
    def config_get_int(config: dict, keys: str, default_value: int) -> Tuple[bool, int]:
        for k in keys:            
            if k in config:
                return True, int(config[k])
        if default_value == None:
            return False, default_value
        return True, default_value


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

    @staticmethod
    def load_provider(config: dict) -> Tuple[DopError, Callable]:
        """
        Return a new provider given the configuration options as
        {
            'path':'/home/ecosteer/monitor/ecosteer/dop/provider/presentation/output/pres_output_rabbitqueue.py',
            'class':'outputRabbitQueue',
            'configuration':'url=amqp://guest:guest@deb10docker:5672/;queue_name=imperatives;rc=10;rd=10;dm=1;'
        }
        """
        
        if ('path' in config) == False:
            return (DopError(1,"configuration missing [path] key"),None)

        if ('configuration' in config) == False:
            return (DopError(2,"configuration missing [configuration] key"),None)
        

        has_class = ('class' in config)
        has_provider = ('provider' in config)
        if (has_class or has_provider) == False:
            return (DopError(3,"configuration missing class key"),None)

        conf_path: str = config['path']
        conf_provider: str = config['provider'] if has_provider else config['class']


        try:
            #   NOTE:
            #   the class name is used as if it were a module.name, too
            #   -   as long as no different modules implements classes with the same name, this should do
            module = SourceFileLoader(conf_provider, conf_path).load_module()
            provider = getattr(module, conf_provider)
            return (DopError(),provider())
        except FileNotFoundError as fe:
            return (DopError(120, "Provider source file not found."), None)
        except Exception as e:
            print(str(e))
            print(traceback.format_exc())
            return (DopError(4,"exception while loading provider"),None)



    @staticmethod 
    def to_base64(input: str) -> Tuple[str, DopError] :
        if len(input) == 0: 
            return "", DopError(1, "empty string")
        try:
            input_bytes = input.encode()
            input_bytes_b64 = base64.standard_b64encode(input_bytes)
            input_b64 = input_bytes_b64.decode()
            return input_b64, DopError(0)
        except Exception as e:
            return "", DopError(2, "exception during base64 transformation")


    @staticmethod
    def create_uuid() -> UUID:
        import uuid 
        return uuid.uuid4()


