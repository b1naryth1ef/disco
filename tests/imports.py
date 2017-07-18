"""
This module tests that all of disco can be imported, mostly to help reduce issues
with untested code that will not even parse/run on Py2/3
"""
from disco.api.client import *
from disco.api.http import *
from disco.api.ratelimit import *
from disco.bot.bot import *
from disco.bot.command import *
from disco.bot.parser import *
from disco.bot.plugin import *
from disco.bot.storage import *
from disco.gateway.client import *
from disco.gateway.events import *
from disco.gateway.ipc import *
from disco.gateway.packets import *
# Not imported, GIPC is required but not provided by default
# from disco.gateway.sharder import *
from disco.types.base import *
from disco.types.channel import *
from disco.types.guild import *
from disco.types.invite import *
from disco.types.message import *
from disco.types.permissions import *
from disco.types.user import *
from disco.types.voice import *
from disco.types.webhook import *
from disco.util.backdoor import *
from disco.util.config import *
from disco.util.functional import *
from disco.util.hashmap import *
from disco.util.limiter import *
from disco.util.logging import *
from disco.util.serializer import *
from disco.util.snowflake import *
from disco.util.token import *
from disco.util.websocket import *
from disco.voice.client import *
from disco.voice.opus import *
from disco.voice.packets import *
from disco.voice.playable import *
from disco.voice.player import *
