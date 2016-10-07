from gevent.backdoor import BackdoorServer


class DiscoBackdoorServer(BackdoorServer):
    def __init__(self, listener, localf=None, banner=None, **server_args):
        super(DiscoBackdoorServer, self).__init__(listener, {}, banner, **server_args)
        self.localf = localf

    def _create_interactive_locals(self):
        obj = super(DiscoBackdoorServer, self)._create_interactive_locals()
        obj.update(self.localf())
        return obj
