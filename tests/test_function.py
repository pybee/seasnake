from tests.utils import GeneratorTestCase


class FunctionTestCase(GeneratorTestCase):
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
