from tests.utils import ConverterTestCase


class StructTestCase(ConverterTestCase):
    def test_empty_struct(self):
        self.assertGeneratedOutput(
            """
            struct Foo {};
            """,
            """
            class Foo:
                pass


            """
        )

    def test_simple_struct(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
                float x;
                float y;
            };
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y


            """
        )
