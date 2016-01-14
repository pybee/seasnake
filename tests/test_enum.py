from tests.utils import GeneratorTestCase


class EnumTestCase(GeneratorTestCase):
    def test_enum_without_values(self):
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

    def test_enum_with_values(self):
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

    def test_enum_with_initial_values(self):
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

    def test_enum_with_multiple_initial_values(self):
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

    def test_empty_enum(self):
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
