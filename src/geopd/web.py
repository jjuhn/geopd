from can.web import create_app

application = create_app('geopd')


def run():
    application.run()
