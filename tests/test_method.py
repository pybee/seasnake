from __future__ import unicode_literals

from tests.utils import ConverterTestCase

from unittest import skip


class MethodTestCase(ConverterTestCase):
    def test_return_nothing(self):
        self.assertGeneratedOutput(
            """
            class Foo {
              public:
                void wibble(int x) {
                    int z = 3;
                    if (z > 10) {
                        return;
                    }
                    return;
                }

            };
            """,
            """
            class Foo:
                def wibble(self, x):
                    z = 3
                    if z > 10:
                        return
                    return
            """
        )

    def test_return_value(self):
        self.assertGeneratedOutput(
            """
            class Foo {
              public:
                int wibble(int x) {
                    int z = 3;
                    if (z > 10) {
                        return 37;
                    }
                    return 42;
                }

            };
            """,
            """
            class Foo:
                def wibble(self, x):
                    z = 3
                    if z > 10:
                        return 37
                    return 42
            """
        )

    def test_use_parameter(self):
        self.assertGeneratedOutput(
            """
            class Foo {
              public:
                int wibble(int x) {
                    if (x > 10) {
                        return 37;
                    }
                    return 42;
                }

            };
            """,
            """
            class Foo:
                def wibble(self, x):
                    if x > 10:
                        return 37
                    return 42
            """
        )

    def test_use_parameter_with_rename(self):
        self.assertGeneratedOutput(
            """
            class Foo {
              public:
                int wibble(int arg);
            };

            int Foo::wibble(int x) {
                if (x > 10) {
                    return 37;
                }
                return 42;
            }

            """,
            """
            class Foo:
                def wibble(self, x):
                    if x > 10:
                        return 37
                    return 42
            """
        )
        
    def test_function_template(self):
        self.assertGeneratedOutput(
            """
            class Test {
                template <typename T>
                void fn(T arg) {}
            };

            """,
            """
            class Test:
                def fn(self, arg):
                    pass
            """
        )
        
    def test_static_function_template(self):
        self.assertGeneratedOutput(
            """
            class Test {
                template <typename T>
                static void fn(T arg) {}
            };

            """,
            """
            class Test:
                @staticmethod
                def fn(arg):
                    pass
            """
        )
