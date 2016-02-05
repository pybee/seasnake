from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class ClassTestCase(ConverterTestCase):
    def test_simple_template(self):
        self.assertGeneratedOutput(
            """
            template<typename T>
            class Foo {};

            void test() {
                Foo<int> *f1 = new Foo<int>();
            }
            """,
            """
            class Foo:
                pass


            def test():
                f1 = Foo()
            """
        )

    def test_template_typedef(self):
        self.assertGeneratedOutput(
            """
            template<typename T>
            class Foo {};

            typedef Foo<int> IntFoo

            void test() {
                IntFoo *f1 = new IntFoo();
            }
            """,
            """
            class Foo:
                pass


            IntFoo = Foo


            def test():
                f1 = IntFoo()
            """
        )
