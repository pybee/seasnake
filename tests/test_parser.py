from unittest import TestCase

from tests.utils import adjust
from seasnake.parser import CppParser


class ParserTestCase(TestCase):
    def assertParser(self, input, output, errors=None, **options):
        parser = CppParser()
        parser.parse(adjust(input))

    def test_enum(self):
        self.assertParser(
            """
            namespace foo {
                enum bar {
                    TOP,
                    RIGHT,
                    BOTTOM,
                    LEFT
                };
            }
            """,
            """


            """
        )
