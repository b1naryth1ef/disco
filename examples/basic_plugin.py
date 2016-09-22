from disco.cli import disco_main
from disco.bot import Bot
from disco.bot.plugin import Plugin


class BasicPlugin(Plugin):
    @Plugin.listen('MessageCreate')
    def on_message_create(self, event):
        print 'Message Created: {}'.format(event.message.content)

    @Plugin.command('test')
    def on_test_command(self, event):
        print 'wtf'

if __name__ == '__main__':
    bot = Bot(disco_main())
    bot.add_plugin(BasicPlugin)
    bot.run_forever()
