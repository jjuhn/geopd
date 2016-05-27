import re


def format_user_input(user_input, capitalize=True):
    s = re.sub('\s+', ' ', user_input.strip())
    if capitalize:
        s = s[0].upper() + s[1:]
    return s


def name2key(name):
    s = ''.join([c.lower() for c in name if c.isalnum() or c == ' '])
    return re.sub('\s+', '_', s)


def to_underscore(camel_case):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_case)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
