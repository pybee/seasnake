'''
This is the main entry point for SeaSnake.
'''
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Convert C++ code to Python.',
    )

    parser.add_argument(
        '-D',
        action='append',
        metavar='definition',
        dest='defines',
        help='Define a preprocessor variable.',
        default=[]
    )

    parser.add_argument(
        'filename',
        metavar='file.cpp',
        help='The file to compile.'
    )

        # parser.add_argument(
    #     'args', nargs=argparse.REMAINDER,
    #     help='Arguments to pass to the script you are debugging.'
    # )

    args = parser.parse_args()


if __name__ == '__main__':
    main()
