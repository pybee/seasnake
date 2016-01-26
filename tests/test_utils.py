from __future__ import unicode_literals

import unittest

from .utils import adjust


class AdjustTests(unittest.TestCase):
    def assertEqualOutput(self, actual, expected):
        self.assertEqual(adjust(actual), adjust(expected))

    def test_adjust(self):
        "Test input can be stripped of leading spaces."
        self.assertEqual("""for i in range(0, 10):
    print('hello, world')
print('Done.')
""", adjust("""
            for i in range(0, 10):
                print('hello, world')
            print('Done.')
        """))

    def test_no_leading_space(self):
        self.assertEqual("""for i in range(0, 10):
    print('hello, world')
print('Done.')
""", adjust("""for i in range(0, 10):
    print('hello, world')
print('Done.')
"""))

    def test_no_leading_space_on_first_line(self):
        self.assertEqual("""

for i in range(0, 10):
    print('hello, world')
print('Done.')
""", adjust("""


            for i in range(0, 10):
                print('hello, world')
            print('Done.')
            """))

    def test_single_line(self):
        self.assertEqual("Hello, world", adjust("Hello, world"))
        self.assertEqual("    Hello, world", adjust("    Hello, world"))
