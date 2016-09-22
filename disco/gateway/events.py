import inflection
import skema

from disco.types.user import User
from disco.types.guild import Guild


class GatewayEvent(skema.Model):
    @staticmethod
    def from_dispatch(obj):
        cls = globals().get(inflection.camelize(obj['t'].lower()))
        if not cls:
            raise Exception('Could not find cls for {}'.format(obj['t']))

        return cls(obj['d'])


class Ready(GatewayEvent):
    version = skema.IntType(stored_name='v')
    session_id = skema.StringType()
    user = skema.ModelType(User)
    guilds = skema.ListType(skema.ModelType(Guild))
