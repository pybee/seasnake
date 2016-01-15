from tests.utils import GeneratorTestCase


class ClassTestCase(GeneratorTestCase):
    def test_empty_class(self):
        self.assertGeneratedOutput(
            """
            class Foo {};
            """,
            """
            class Foo:
                pass


            """
        )

    def test_empty_class_with_super(self):
        self.assertGeneratedOutput(
            """
            class Bar {};
            class Foo : public Bar {};
            """,
            """
            class Bar:
                pass


            class Foo(Bar):
                pass


            """
        )

    def test_empty_class_with_super(self):
        self.assertGeneratedOutput(
            """
            class Bar {};
            class Foo : public Bar {};
            """,
            """
            class Bar:
                pass


            class Foo(Bar):
                pass


            """
        )
