'''
This is the main entry point for SeaSnake.
'''
import argparse

from seasnake import VERSION


def main():
    parser = argparse.ArgumentParser(
        description='A tool to manage conversion of C++ code to Python.',
        version=VERSION
    )

    # parser.add_argument(
    #     'filename',
    #     metavar='script.py',
    #     help='The script to debug.'
    # )
    # parser.add_argument(
    #     'args', nargs=argparse.REMAINDER,
    #     help='Arguments to pass to the script you are debugging.'
    # )

    args = parser.parse_args()


if __name__ == '__main__':
    main()
