from disco.bot import Plugin


class BasicPlugin(Plugin):
    @Plugin.command('reload')
    def on_reload(self, event):
        self.reload()
        event.msg.reply('Reloaded!')

    @Plugin.listen('MessageCreate')
    def on_message_create(self, msg):
        self.log.info('Message created: {}: {}'.format(msg.author, msg.content))

    @Plugin.command('echo', '<content:str...>')
    def on_test_command(self, event, content):
        event.msg.reply(content)

    @Plugin.command('spam', '<count:int> <content:str...>')
    def on_spam_command(self, event, count, content):
        for i in range(count):
            event.msg.reply(content)

    @Plugin.command('count', group='messages')
    def on_stats(self, event):
        msg = event.msg.reply('Ok, one moment...')
        msg_count = 0

        for msgs in event.channel.messages_iter(bulk=True):
            msg_count += len(msgs)

        msg.edit('{} messages'.format(msg_count))

    @Plugin.command('tag', '<name:str> [value:str...]')
    def on_tag(self, event, name, value=None):
        tags = self.storage.guild.ensure('tags')

        if value:
            tags[name] = value
            event.msg.reply(':ok_hand:')
        else:
            if name in tags:
                return event.msg.reply(tags[name])
            else:
                return event.msg.reply('Unknown tag: `{}`'.format(name))

    @Plugin.command('info', '<query:str...>')
    def on_info(self, event, query):
        users = list(self.state.users.select({'username': query}, {'id': query}))

        if not users:
            event.msg.reply("Couldn't find user for your query: `{}`".format(query))
        elif len(users) > 1:
            event.msg.reply('I found too many userse ({}) for your query: `{}`'.format(len(users), query))
        else:
            user = users[0]
            parts = []
            parts.append('ID: {}'.format(user.id))
            parts.append('Username: {}'.format(user.username))
            parts.append('Discriminator: {}'.format(user.discriminator))

            if event.channel.guild:
                member = event.channel.guild.get_member(user)
                parts.append('Nickname: {}'.format(member.nick))
                parts.append('Joined At: {}'.format(member.joined_at))

            event.msg.reply('```\n{}\n```'.format(
                '\n'.join(parts)
            ))
