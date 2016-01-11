import contextlib
from io import StringIO
import sys
import traceback


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
