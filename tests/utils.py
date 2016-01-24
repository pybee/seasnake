import contextlib
from io import StringIO
import sys
import traceback
from unittest import TestCase

from seasnake.parser import CodeConverter


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


class ConverterTestCase(TestCase):
    def assertGeneratedOutput(self, cpp, py, flags=None):
        converter = CodeConverter('test')

        # Parse the content
        converter.parse_text(files=[('test.cpp', adjust(cpp))], flags=flags)

        # Output the generated code
        buf = StringIO()
        converter.output('test', buf)

        # Compare the generated code to expectation.
        self.assertEqual(adjust(py), buf.getvalue())

    def assertMultifileGeneratedOutput(self, cpp, py, flags=None):
        converter = CodeConverter('test')

        # Parse the content of each file
        converter.parse_text(
            files=[
                (name, adjust(content))
                for name, content in cpp
            ],
            flags=flags
        )

        # Output each generated code file
        for module, content in py:
            buf = StringIO()
            converter.output(module, buf)

            # Compare the generated code to expectation.
            self.assertEqual(adjust(content), buf.getvalue(), "Discrepancy in %s" % module)
