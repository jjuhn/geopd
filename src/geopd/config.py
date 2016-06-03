import ConfigParser
import os.path

CONFIG_VARNAME = 'GEOPD_CONFIG_PATH'

if CONFIG_VARNAME not in os.environ:
    raise RuntimeError("environment variable {0} is not set".format(CONFIG_VARNAME))

try:
    with open(os.environ[CONFIG_VARNAME]) as config_file:
        config = ConfigParser.ConfigParser()
        config.readfp(config_file)
except EnvironmentError as e:
    raise RuntimeError("failed to load configuration: {0}".format(e))
