from tests.utils import GeneratorTestCase

from unittest import skip


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

    def test_empty_constructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                Foo() {

                }
            };
            """,
            """
            class Foo:
                def __init__(self):
                    pass


            """
        )

    def test_empty_constructor_with_param(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                Foo(int x) {

                }
            };
            """,
            """
            class Foo:
                def __init__(self, x):
                    pass


            """
        )

    def test_constructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

                Foo(int x) {
                    this.m_x = x;
                }

            };
            """,
            """
            class Foo:
                def __init__(self, x):
                    self.m_x = x


            """
        )

    @skip("C++11 features not yet supported")
    def test_initialized_field(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x = 42;

                Foo() {
                }

            };
            """,
            """
            class Foo:
                def __init__(self):
                    self.m_x = 42


            """
        )

    def test_uninitialized_field(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

                Foo() {
                }

            };
            """,
            """
            class Foo:
                def __init__(self):
                    pass


            """
        )

    def test_destructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

                ~Foo() {
                    this.m_x = 0;
                }

            };
            """,
            """
            class Foo:
                def __del__(self):
                    self.m_x = 0


            """
        )
