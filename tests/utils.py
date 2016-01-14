import contextlib
from io import StringIO
import sys
import traceback
from unittest import TestCase

from seasnake.generator import Generator


@contextlib.contextmanager
def capture_output(redirect_stderr=True):
    oldout, olderr = sys.stdout, sys.stderr
    try:
        out = StringIO()
        sys.stdout = out
        if redirect_stderr:
            sys.stderr = out
        else:
            sys.stderr = StringIO()
        yield out
    except:
        if redirect_stderr:
            traceback.print_exc()
        else:
            raise
    finally:
        sys.stdout, sys.stderr = oldout, olderr


def adjust(text):
    """Adjust a code sample to remove leading whitespace."""
    lines = text.split('\n')
    if len(lines) == 1:
        return text

    if lines[0].strip() == '':
        lines = lines[1:]

    final_lines = []
    first_line = lines[0].lstrip()
    while len(first_line) == 0:
        final_lines.append('')
        lines = lines[1:]
        try:
            first_line = lines[0].lstrip()
        except IndexError:
            first_line = None
            break

    if first_line is not None:
        n_spaces = len(lines[0]) - len(first_line)
        final_lines.extend([line[n_spaces:] for line in lines])

    return '\n'.join(final_lines)


class GeneratorTestCase(TestCase):
    def assertGeneratedOutput(self, input, output, header=None):
        generator = Generator('test')

        # Parse the content
        generator.parse_text('testfile.cpp', adjust(input))
        if header:
            generator.parse_text('testfile.h', adjust(header))

        # Output the generated code
        buf = StringIO()
        generator.module.output(buf)

        # Compare the generated code to expectation.
        self.assertEqual(adjust(output), buf.getvalue())
