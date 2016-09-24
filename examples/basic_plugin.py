from disco.cli import disco_main
from disco.bot import Bot
from disco.bot.plugin import Plugin


class BasicPlugin(Plugin):
    @Plugin.listen('MessageCreate')
    def on_message_create(self, event):
        self.log.info('Message created: <{}>: {}'.format(
            event.message.author.username,
            event.message.content))

    @Plugin.command('echo', '<content:str...>')
    def on_test_command(self, event, content):
        event.msg.reply(content)

    @Plugin.command('spam', '<count:int> <content:str...>')
    def on_spam_command(self, event, count, content):
        for i in range(count):
            event.msg.reply(content)

    @Plugin.command('invites')
    def on_invites(self, event):
        invites = event.channel.get_invites()
        event.msg.reply('Channel has a total of {} invites'.format(len(invites)))

    @Plugin.command('pins')
    def on_pins(self, event):
        pins = event.channel.get_pins()
        event.msg.reply('Channel has a total of {} pins'.format(len(pins)))

    @Plugin.command('channel stats')
    def on_stats(self, event):
        msg = event.msg.reply('Ok, one moment...')
        invite_count = len(event.channel.get_invites())
        pin_count = len(event.channel.get_pins())
        msg_count = 0

        print event.channel.messages_iter(bulk=True)
        for msgs in event.channel.messages_iter(bulk=True):
            msg_count += len(msgs)

        msg.edit('{} invites, {} pins, {} messages'.format(invite_count, pin_count, msg_count))

    @Plugin.command('messages stack')
    def on_messages_stack(self, event):
        event.msg.reply('Channels: {}, messages here: ```\n{}\n```'.format(
            len(self.state.messages),
            '\n'.join([str(i.id) for i in self.state.messages[event.channel.id]])
        ))

if __name__ == '__main__':
    bot = Bot(disco_main())
    bot.add_plugin(BasicPlugin)
    bot.run_forever()
