from disco.bot import Plugin


class BasicPlugin(Plugin):
    def load(self, ctx):
        super(BasicPlugin, self).load(ctx)
        self.tags = self.storage.guild('tags')

    @Plugin.command('add', '<name:str> <value:str...>', group='tags')
    def on_tags_add(self, event, name, value):
        if name in self.tags:
            return event.msg.reply('That tag already exists!')

        self.tags[name] = value
        return event.msg.reply(u':ok_hand: created the tag {}'.format(name), sanitize=True)

    @Plugin.command('get', '<name:str>', group='tags')
    def on_tags_get(self, event, name):
        if name not in self.tags:
            return event.msg.reply('That tag does not exist!')

        return event.msg.reply(self.tags[name], sanitize=True)

    @Plugin.command('delete', '<name:str>', group='tags', aliases=['del', 'rmv', 'remove'])
    def on_tags_delete(self, event, name):
        if name not in self.tags:
            return event.msg.reply('That tag does not exist!')

        del self.tags[name]

        return event.msg.reply(u':ok_hand: I deleted the {} tag for you'.format(
            name
        ), sanitize=True)
