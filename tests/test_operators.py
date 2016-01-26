from __future__ import unicode_literals

from tests.utils import ConverterTestCase

from unittest import expectedFailure


class LiteralsTestCase(ConverterTestCase):
    @expectedFailure
    def test_unary_operators(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 37;

                x++;
                x--;
                ++x;
                --x;
            }
            """,
            """
            def test():
                x = 37
                x += 1
                x += 1
                y -= 1
                y -= 1
            """
        )

    @expectedFailure
    def test_unary_operator_assignment_behavior(self):
        # The C++ unary operator has some specific behavior
        # when interacting with assignment operations. Make
        # sure this is honored.
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 37;
                int y = 42

                y = x++;
                y = x--;
                y = ++x;
                y = --x;
            }
            """,
            """
            def test():
                x = 37
                y = 42
                x = y
                x += 1
                x = y
                x -= 1
                x += 1
                x = y
                x -= 1
                x = y
            """
        )

    def test_arithmetic_operators(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 37;
                int y = 42;
                int z;

                z = x + y;
                z = x - y;
                z = x * y;
                z = x / y;
                z = x % y;
            }
            """,
            """
            def test():
                x = 37
                y = 42
                z = x + y
                z = x - y
                z = x * y
                z = x / y
                z = x % y
            """
        )

    def test_comparison_operators(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 37;
                int y = 42;
                bool z;

                z = x == y;
                z = x != y;
                z = x > y;
                z = x < y;
                z = x >= y;
                z = x <= y;
            }
            """,
            """
            def test():
                x = 37
                y = 42
                z = x == y
                z = x != y
                z = x > y
                z = x < y
                z = x >= y
                z = x <= y
            """
        )

    def test_bitwise_operators(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 37;
                int y = 42;
                int z;

                z = x & y;
                z = x | y;
                z = x ^ y;
                z = ~x;
                z = x << y;
                z = x >> y;
            }
            """,
            """
            def test():
                x = 37
                y = 42
                z = x & y
                z = x | y
                z = x ^ y
                z = ~x
                z = x << y
                z = x >> y
            """
        )

    def test_assignment_operators(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 37;
                int y = 42;

                y += x;
                y -= x;
                y *= x;
                y /= x;
                y %= x;
                y <<= x;
                y >>= x;
                y &= x;
                y ^= x;
                y |= x;
            }
            """,
            """
            def test():
                x = 37
                y = 42
                y += x
                y -= x
                y *= x
                y /= x
                y %= x
                y <<= x
                y >>= x
                y &= x
                y ^= x
                y |= x
            """
        )

    def test_logical_operators(self):
        self.assertGeneratedOutput(
            """
            void test() {
                bool x = true;
                bool y = false;
                bool z;

                z = x && y;
                z = x || y;
                z = !x;
            }
            """,
            """
            def test():
                x = True
                y = False
                z = x and y
                z = x or y
                z = not x
            """
        )

    def test_comparison_operator(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 37;
                int y = 42;
                int z;
                z = x > y ? x : y;
            }
            """,
            """
            def test():
                x = 37
                y = 42
                z = x if x > y else y
            """
        )
