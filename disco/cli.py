import logging
import argparse

from gevent import monkey

parser = argparse.ArgumentParser()
parser.add_argument('--token', help='Bot Authentication Token', required=True)

logging.basicConfig(level=logging.INFO)


def main():
    monkey.patch_all()
    args = parser.parse_args()

    from disco.util.token import is_valid_token

    if not is_valid_token(args.token):
        print 'Invalid token passed'
        return

    from disco.client import DiscoClient
    DiscoClient(args.token).run_forever()

if __name__ == '__main__':
    main()
