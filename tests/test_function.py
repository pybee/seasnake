from tests.utils import ConverterTestCase


class FunctionTestCase(ConverterTestCase):
    def test_empty(self):
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

    def test_simple(self):
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

    def test_function_call(self):
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

    def test_nested_call(self):
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

    def test_default_args(self):
        self.assertGeneratedOutput(
            """
            float distance(int x, int y, int z = 0) {
                return x^2 + y^2 + z^2;
            }

            void test() {
                float d1 = distance(10, 10);
                float d2 = distance(5, 5, 5);
            }
            """,
            """
            def distance(x, y, z=0):
                return x**2 + y**2 + z**2


            def test():
                d1 = distance(10, 10)
                d2 = distance(5, 5, 5)


            """
        )
