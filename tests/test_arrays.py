from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class ArraysTestCase(ConverterTestCase):
    def test_const_index(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int foo[3] = {37, 42, 69};
                int answer;

                answer = foo[1];
            }
            """,
            """
            def test():
                foo = [37, 42, 69]
                answer = foo[1]
            """
        )

    def test_var_index(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int foo[3] = {37, 42, 69};
                int index = 1;
                int answer;

                answer = foo[index];
            }
            """,
            """
            def test():
                foo = [37, 42, 69]
                index = 1
                answer = foo[index]
            """
        )
