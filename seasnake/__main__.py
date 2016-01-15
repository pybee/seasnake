'''
This is the main entry point for SeaSnake.
'''
import argparse
import sys

from seasnake.generator import Generator


def main():
    opts = argparse.ArgumentParser(
        description='Convert C++ code to Python.',
    )

    opts.add_argument(
        'filename',
        metavar='file.cpp',
        help='The file(s) to compile.',
        nargs="+"
    )

    args = opts.parse_args()

    generator = Generator('Test')
    for filename in args.filename:
        generator.parse(filename)

    generator.module.output(sys.stdout)


if __name__ == '__main__':
    main()
