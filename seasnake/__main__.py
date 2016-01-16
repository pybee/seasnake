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
        '-o',
        '--output',
        metavar='module',
        help='The name of the output module to write.',
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

    if args.output:
        with open('%s.py' % args.output, 'w') as out:
            generator.output(out)
    else:
        generator.output(sys.stdout)


if __name__ == '__main__':
    main()
