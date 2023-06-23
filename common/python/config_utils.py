#   ver:    1.1
#   date:   14/06/2023
#   author: georgiana-bud

from common.python.error import DopError


class ConfigUtils:

    @staticmethod
    def config_to_dict(connstring: str) -> tuple[DopError, dict]:
        if connstring == "":
            return (DopError(), {})

        conf: dict = {}
        d_conn: list = connstring.split(';')
        for d_conn_item in d_conn:
            if len(d_conn_item) > 0:
                d_item = d_conn_item.split('=')
                conf.update({d_item[0].strip():d_item[1].strip()})
        return DopError(), conf

    @staticmethod
    def config_get_string(config: dict, keys: list, default_value: str) -> tuple[bool, str]:
        for k in keys:            
            if k in config:
                return True, config[k]
        if default_value == None:
            return False, default_value
        return True, default_value
        
    @staticmethod
    def config_get_int(config: dict, keys: str, default_value: int) -> tuple[bool,int]:
        for k in keys:            
            if k in config:
                return True, int(config[k])
        if default_value == None:
            return False, default_value
        return True, default_value




