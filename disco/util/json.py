from __future__ import absolute_import

from json import dumps

try:
    from rapidjson import loads
except ImportError:
    print '[WARNING] rapidjson not installed, falling back to default Python JSON parser'
    from json import loads

__all__ = ['dumps', 'loads']
