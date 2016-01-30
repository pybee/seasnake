###########################################################################
# Code Writer
#
# This is a helper that can be used to write code; it knows how to
# maintain the right number of spaces between code blocks to remain PEP8
# compliant.
###########################################################################
from __future__ import unicode_literals, print_function


class CodeWriter(object):
    def __init__(self, out, preamble=None):
        self.out = out
        self.line_cleared = True
        self.blank_lines = 2
        self.depth = 0
        self.empty = True

        if preamble:
            self.out.write(preamble)

    def write(self, content):
        if not self.empty:
            for i in range(0, self.blank_lines):
                self.out.write('\n')
        self.blank_lines = 0
        if content:
            if self.line_cleared:
                self.out.write('    ' * self.depth)
            self.out.write(content)
            self.empty = False
            self.line_cleared = False

    def clear_line(self):
        if not self.line_cleared:
            self.out.write('\n')
            self.line_cleared = True
            self.blank_lines = 0

    def clear_minor_block(self):
        if not self.line_cleared:
            self.out.write('\n')
            self.line_cleared = True
        while self.blank_lines < 1:
            self.blank_lines += 1

    def clear_major_block(self):
        if not self.line_cleared:
            self.out.write('\n')
            self.line_cleared = True
        while self.blank_lines < max(1, 2 - self.depth):
            self.blank_lines += 1

    def start_block(self):
        self.empty = True
        self.depth += 1
        self.blank_lines = 2

    def end_block(self):
        self.depth -= 1
