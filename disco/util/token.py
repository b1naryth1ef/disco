import re

TOKEN_RE = re.compile(r'M\w{23}\.[\w-]{6}\..{27}')


def is_valid_token(token):
    """
    Validates a Discord authentication token, returning true if valid
    """
    return bool(TOKEN_RE.match(token))
