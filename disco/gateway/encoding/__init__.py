from .json import JSONEncoder

ENCODERS = {
    'json': JSONEncoder,
}

try:
    from .etf import ETFEncoder
    ENCODERS['etf'] = ETFEncoder
except ImportError:
    pass
