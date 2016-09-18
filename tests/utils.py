from __future__ import unicode_literals

import contextlib
from io import StringIO
import sys
import traceback
from unittest import TestCase

from seasnake.parser import CodeConverter


@contextlib.contextmanager
def capture_output(redirect_stdout=True, redirect_stderr=True):
    oldout, olderr = sys.stdout, sys.stderr
    try:
        out = StringIO()
        if redirect_stdout:
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
    def assertGeneratedOutput(self, cpp, py, errors=None, flags=None):
        self.maxDiff = None
        converter = CodeConverter('test')

        # Parse the content
        with capture_output(redirect_stdout=False) as console:
            converter.parse_text(
                [
                    ('test.cpp', adjust(cpp))
                ],
                flags=flags if flags else ['-std=c++0x']
            )

        if errors:
            self.assertEqual(adjust(errors), console.getvalue())
        else:
            self.assertEqual('', console.getvalue())

        # Output the generated code
        buf = StringIO()
        converter.output('test', buf)

        # Compare the generated code to expectation.
        self.assertEqual(adjust(py), buf.getvalue())

    def assertMultifileGeneratedOutput(self, cpp, py, errors=None, flags=None):
        self.maxDiff = None
        converter = CodeConverter('test')

        # Parse the content of each file
        with capture_output(redirect_stdout=False) as console:
            converter.parse_text(
                [
                    (filename, adjust(content))
                    for filename, content in cpp
                ],
                flags=flags if flags else ['-std=c++0x']
            )

        if errors is not None:
            self.assertEqual(adjust(errors), console.getvalue())
        else:
            self.assertEqual('', console.getvalue())

        # Output each generated code file
        for module, content in py:
            buf = StringIO()
            converter.output(module, buf)

            # Compare the generated code to expectation.
            self.assertEqual(adjust(content), buf.getvalue())
