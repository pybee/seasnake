from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class EnumTestCase(ConverterTestCase):

    def test_empty(self):
        self.assertGeneratedOutput(
            """
            enum Bar {
            };
            """,
            """
            from enum import Enum


            class Bar(Enum):
                pass
            """
        )

    def test_without_values(self):
        self.assertGeneratedOutput(
            """
            enum Bar {
                TOP,
                RIGHT,
                BOTTOM,
                LEFT
            };
            """,
            """
            from enum import Enum


            class Bar(Enum):
                TOP = 0
                RIGHT = 1
                BOTTOM = 2
                LEFT = 3
            """
        )

    def test_values(self):
        self.assertGeneratedOutput(
            """
            enum Bar {
                TOP = 37,
                RIGHT = 42,
                BOTTOM = 55,
                LEFT = 69
            };
            """,
            """
            from enum import Enum


            class Bar(Enum):
                TOP = 37
                RIGHT = 42
                BOTTOM = 55
                LEFT = 69
            """
        )

    def test_initial_values(self):
        self.assertGeneratedOutput(
            """
            enum Bar {
                TOP = 37,
                RIGHT,
                BOTTOM,
                LEFT
            };
            """,
            """
            from enum import Enum


            class Bar(Enum):
                TOP = 37
                RIGHT = 38
                BOTTOM = 39
                LEFT = 40
            """
        )

    def test_multiple_initial_values(self):
        self.assertGeneratedOutput(
            """
            enum Bar {
                TOP = 37,
                RIGHT,
                BOTTOM = 42,
                LEFT
            };
            """,
            """
            from enum import Enum


            class Bar(Enum):
                TOP = 37
                RIGHT = 38
                BOTTOM = 42
                LEFT = 43
            """
        )

    def test_expressions_for_values(self):
        self.assertGeneratedOutput(
            """
                enum Bar {
                    TOP = 1 << 0,
                    RIGHT = 1 << 1,
                    BOTTOM = 1 << 2,
                    LEFT = 1 << 3
                };
            """,
            """
            from enum import Enum


            class Bar(Enum):
                TOP = 1
                RIGHT = 2
                BOTTOM = 4
                LEFT = 8
            """
        )

    def test_local_enum_reference(self):
        self.assertGeneratedOutput(
            """
                enum Bar {
                    TOP,
                    RIGHT,
                    BOTTOM,
                    LEFT
                };

                void test() {
                    Bar position = TOP;
                }
            """,
            """
            from enum import Enum


            class Bar(Enum):
                TOP = 0
                RIGHT = 1
                BOTTOM = 2
                LEFT = 3


            def test():
                position = Bar.TOP
            """
        )
