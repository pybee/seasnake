from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class FunctionTestCase(ConverterTestCase):
    def test_inline_empty(self):
        self.assertGeneratedOutput(
            """
            void empty() {

            }
            """,
            """
            def empty():
                pass
            """
        )

    def test_inline_simple(self):
        self.assertGeneratedOutput(
            """
            int double_value(int in) {
                int out;

                out = in * 2;

                return out;
            }
            """,
            """
            def double_value(in):
                out = in * 2
                return out
            """
        )

    def test_inline_function_call(self):
        self.assertGeneratedOutput(
            """
            void ping() {

            }

            int double_value(int in) {
                int out;

                out = in * 2;

                return out;
            }

            void test() {
                int value = 42;

                ping();

                double_value(37);

                int result = double_value(value);
            }
            """,
            """
            def ping():
                pass


            def double_value(in):
                out = in * 2
                return out


            def test():
                value = 42
                ping()
                double_value(37)
                result = double_value(value)
            """
        )

    def test_inline_nested_call(self):
        self.assertGeneratedOutput(
            """
            int triple_value(int in) {
                return 3 * in;
            }

            int double_value(int in) {
                int out;

                out = in * 2;

                return out;
            }

            void test() {
                int result = double_value(triple_value(37));
            }
            """,
            """
            def triple_value(in):
                return 3 * in


            def double_value(in):
                out = in * 2
                return out


            def test():
                result = double_value(triple_value(37))
            """
        )

    def test_inline_default_args(self):
        self.assertGeneratedOutput(
            """
            float distance(int x, int y, int z = 0) {
                return x*x + y*y + z*z;
            }

            void test() {
                float d1 = distance(10, 10);
                float d2 = distance(5, 5, 5);
            }
            """,
            """
            def distance(x, y, z=0):
                return x * x + y * y + z * z


            def test():
                d1 = distance(10, 10)
                d2 = distance(5, 5, 5)
            """
        )

    def test_empty(self):
        self.assertGeneratedOutput(
            """
            void empty();

            void empty() {

            }
            """,
            """
            def empty():
                pass
            """
        )

    def test_simple(self):
        self.assertGeneratedOutput(
            """
            int double_value(int in);

            int double_value(int in) {
                int out;

                out = in * 2;

                return out;
            }
            """,
            """
            def double_value(in):
                out = in * 2
                return out
            """
        )

    def test_function_call(self):
        self.assertGeneratedOutput(
            """
            void ping();
            int double_value(int in);
            void test();

            void ping() {

            }

            int double_value(int in) {
                int out;

                out = in * 2;

                return out;
            }

            void test() {
                int value = 42;

                ping();

                double_value(37);

                int result = double_value(value);
            }
            """,
            """
            def ping():
                pass


            def double_value(in):
                out = in * 2
                return out


            def test():
                value = 42
                ping()
                double_value(37)
                result = double_value(value)
            """
        )

    def test_nested_call(self):
        self.assertGeneratedOutput(
            """
            int triple_value(int in);
            int double_value(int in);
            void test();

            int triple_value(int in) {
                return 3 * in;
            }

            int double_value(int in) {
                int out;

                out = in * 2;

                return out;
            }

            void test() {
                int result = double_value(triple_value(37));
            }
            """,
            """
            def triple_value(in):
                return 3 * in


            def double_value(in):
                out = in * 2
                return out


            def test():
                result = double_value(triple_value(37))
            """
        )

    def test_default_args(self):
        self.assertGeneratedOutput(
            """
            float distance(int x, int y, int z = 0) {
                return x*x + y*y + z*z;
            }

            void test() {
                float d1 = distance(10, 10);
                float d2 = distance(5, 5, 5);
            }
            """,
            """
            def distance(x, y, z=0):
                return x * x + y * y + z * z


            def test():
                d1 = distance(10, 10)
                d2 = distance(5, 5, 5)
            """
        )

    def test_default_attribute_args(self):
        self.assertGeneratedOutput(
            """
            struct Temperature {
                const static int HOT = 1;
                const static int COLD = 0;
            };

            float distance(int x, int y, int temp=Temperature::COLD) {
                return x*x + y*y;
            }

            void test() {
                float d1 = distance(10, 10);
                float d2 = distance(5, 5, 5);
            }
            """,
            """
            class Temperature:
                HOT = 1
                COLD = 0


            def distance(x, y, temp=Temperature.COLD):
                return x * x + y * y


            def test():
                d1 = distance(10, 10)
                d2 = distance(5, 5, 5)
            """
        )

    def test_prototype_without_arg_names(self):
        self.assertGeneratedOutput(
            """
            int double_value(int);

            int double_value(int in) {
                int out;

                out = in * 2;

                return out;
            }
            """,
            """
            def double_value(in):
                out = in * 2
                return out
            """
        )

    def test_prototype_with_different_arg_names(self):
        self.assertGeneratedOutput(
            """
            int double_value(int input);

            int double_value(int in) {
                int out;

                out = in * 2;

                return out;
            }
            """,
            """
            def double_value(in):
                out = in * 2
                return out
            """
        )
