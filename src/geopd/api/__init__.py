from can.web.api import create_api

create_api([
    'geopd.api.users',
    'geopd.api.surveys',
    'geopd.api.user_surveys',
    'geopd.api.cores',
    'geopd.api.posts'
])
