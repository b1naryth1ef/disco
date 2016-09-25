from __future__ import print_function

import logging
import argparse

from gevent import monkey

monkey.patch_all()
parser = argparse.ArgumentParser()
parser.add_argument('--token', help='Bot Authentication Token', required=True)

logging.basicConfig(level=logging.INFO)


def disco_main():
    args = parser.parse_args()

    from disco.util.token import is_valid_token

    if not is_valid_token(args.token):
        print('Invalid token passed')
        return

    from disco.client import DiscoClient
    return DiscoClient(args.token)

if __name__ == '__main__':
    disco_main().run_forever()
