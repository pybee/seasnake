from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class UnionTestCase(ConverterTestCase):
    def test_empty_union(self):
        self.assertGeneratedOutput(
            """
            union Foo {};
            """,
            """
            class Foo:
                pass
            """
        )

    def test_simple_union(self):
        self.assertGeneratedOutput(
            """
            union Foo {
                int x;
                float y;
            };

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();
            }
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )

    def test_predeclaration(self):
        self.assertGeneratedOutput(
            """
            union Foo {
                int x;
                float y;
            };

            union Foo;

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();
            }
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )
