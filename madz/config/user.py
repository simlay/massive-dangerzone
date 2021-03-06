"""config/user.py
@OffbyOne Studios 2013
Manages the configuration of systems from the users perspective.
"""
import os
import logging

from .base import *

logger = logging.getLogger(__name__)

#
# Config
#

class UserConfigNotFoundError(ConfigError): pass

class UserConfig(BaseConfig):
    """An unlabled config applied by the user.

    This represents the information provided by the user prior to use of the a madz project.
    """

    @classmethod
    def load_from_filename(cls, filename):
        import sys
        import traceback
        import imp
        if (not (filename is None)) and os.path.exists(filename):
            with open(filename) as module_file: #TODO(Mason): Figure out this name
                module = imp.load_module("a_config", module_file, filename, ('.py', 'r', imp.PY_SOURCE))
                config = getattr(module, "config")
                if isinstance(config, UserConfig):
                    return config
                else:
                    raise UserConfigNotFoundError("Did not find a UserConfig in the 'config' var of '{}'.")
        logger.info("Skipping user config. File not found '{}'.".format(filename))
                    
        return cls.make_default()

    @classmethod
    def load_from_env_var(cls, env_var):
        """Returns a UserConfig object from an environment variable.
        
        Args:
            env_var: A string representing an environment variable
            
        Returns:
            A UserConfig object.
        """
        return cls.load_from_filename(os.environ.get(env_var))


#
# Options
#

