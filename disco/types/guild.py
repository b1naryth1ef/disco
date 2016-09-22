import skema

from disco.util.oop import TypedClass


class Guild(skema.Model):
    id = skema.SnowflakeType()
