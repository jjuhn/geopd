from importlib import import_module

from can.web import create_app
from can.web import create_blueprint

application = create_app('geopd')
blueprint = create_blueprint()

import_module('geopd.view')
import_module('geopd.api')


def run():
    application.run()
