from importlib import import_module


for name in [
    'geopd.api.users',
    'geopd.api.surveys',
    'geopd.api.user_surveys',
    'geopd.api.cores',
    'geopd.api.posts',
    'geopd.api.projects',
    'geopd.api.pictures']:

    import_module(name)



