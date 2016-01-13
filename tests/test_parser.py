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
            enum Bar {
                TOP,
                RIGHT,
                BOTTOM,
                LEFT
            };
            """,
            """


            """
        )

    def test_enum_class(self):
        self.assertParser(
            """
            enum class Bar {
                TOP,
                RIGHT,
                BOTTOM,
                LEFT
            };
            """,
            """


            """
        )
