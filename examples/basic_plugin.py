from disco.cli import disco_main
from disco.bot import Bot
from disco.bot.plugin import Plugin


class BasicPlugin(Plugin):
    @Plugin.listen('MessageCreate')
    def on_message_create(self, event):
        print 'Message Created: {}'.format(event.message.content)

    @Plugin.command('test')
    def on_test_command(self, event):
        event.msg.reply('HELLO WORLD')

    @Plugin.command('spam')
    def on_spam_command(self, event):
        count = int(event.args[0])

        for i in range(count):
            print event.msg.reply(' '.join(event.args[1:])).id

if __name__ == '__main__':
    bot = Bot(disco_main())
    bot.add_plugin(BasicPlugin)
    bot.run_forever()
