from __future__ import print_function

import logging
import argparse

from gevent import monkey

monkey.patch_all()
parser = argparse.ArgumentParser()
parser.add_argument('--token', help='Bot Authentication Token', required=True)
parser.add_argument('--shard-count', help='Total number of shards', default=1)
parser.add_argument('--shard-id', help='Current shard number/id', default=0)

logging.basicConfig(level=logging.INFO)


def disco_main():
    args = parser.parse_args()

    from disco.util.token import is_valid_token

    if not is_valid_token(args.token):
        print('Invalid token passed')
        return

    from disco.client import DiscoClient
    return DiscoClient.from_cli(args)

if __name__ == '__main__':
    disco_main().run_forever()
