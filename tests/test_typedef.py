from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class StructTestCase(ConverterTestCase):
    def test_typedef_primitives(self):
        self.assertGeneratedOutput(
            """
            typedef unsigned foo1;
            typedef unsigned short foo2;
            typedef unsigned int foo3;
            typedef unsigned long foo4;
            typedef unsigned long long foo5;
            typedef signed foo6;
            typedef short foo7;
            typedef int foo8;
            typedef long foo9;
            typedef long long foo10;

            typedef float bar1;
            typedef double bar2;
            """,
            """
            foo1 = int

            foo2 = int

            foo3 = int

            foo4 = int

            foo5 = int

            foo6 = int

            foo7 = int

            foo8 = int

            foo9 = int

            foo10 = int

            bar1 = float

            bar2 = float
            """
        )

    def test_typedef_commutative(self):
        self.assertGeneratedOutput(
            """
            typedef int foo1;
            typedef foo1 foo2;
            """,
            """
            foo1 = int

            foo2 = foo1
            """
        )

    def test_typedef_struct(self):
        self.assertGeneratedOutput(
            """
            typedef struct {
                float x;
                float y;
            } Foo;
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y
            """
        )

    def test_typedef_named_struct(self):
        self.assertGeneratedOutput(
            """
            typedef struct Foo {
                float x;
                float y;
            } Bar;
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y


            Bar = Foo
            """
        )
