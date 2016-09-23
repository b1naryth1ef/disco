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

if __name__ == '__main__':
    bot = Bot(disco_main())
    bot.add_plugin(BasicPlugin)
    bot.run_forever()
