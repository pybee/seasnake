from tests.utils import ConverterTestCase


class LiteralsTestCase(ConverterTestCase):
    def test_integer_literals(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int int0 = 0;
                int int1 = 1000;
                int int2 = -1000;

                int hex0 = 0x0;
                int hex0a = 0x00;
                int hex0b = 0x0000;
                int hex1 = 0xa;
                int hex1a = 0xab;
                int hex1b = 0xabcd;
                int hex1c = 0xABCD;
                int hex1d = 0x12ABCD34;
                int hex3 = -0xa;
                int hex3a = -0xab;
                int hex3b = -0xabcd;
                int hex3c = -0xABCD;
                int hex3d = -0x12ABCD34;

                int oct1 = 01;
                int oct2 = 012;
                int oct3 = 0123;
                int oct4 = -01;
                int oct5 = -012;
                int oct6 = -0123;
            }
            """,
            """
            def test():
                int0 = 0
                int1 = 1000
                int2 = -1000
                hex0 = 0x0
                hex0a = 0x00
                hex0b = 0x0000
                hex1 = 0xa
                hex1a = 0xab
                hex1b = 0xabcd
                hex1c = 0xABCD
                hex1d = 0x12ABCD34
                hex3 = -0xa
                hex3a = -0xab
                hex3b = -0xabcd
                hex3c = -0xABCD
                hex3d = -0x12ABCD34
                oct1 = 01
                oct2 = 012
                oct3 = 0123
                oct4 = -01
                oct5 = -012
                oct6 = -0123


            """
        )

    def test_int_cast(self):
        self.assertGeneratedOutput(
            """
            void test() {
                float var = 3.14159;
                int foo = (int) var;

            }
            """,
            """
            def test():
                var = 3.14159
                foo = int(var)


            """
        )

    def test_float_literals(self):
        self.assertGeneratedOutput(
            """
            void test() {
                float float1 = 1.2345;
                float float2 = -1.2345;

                float float3 = 1.2345e6;
                float float4 = -1.2345e6;

                float float5 = 1.2345e-6;
                float float6 = -1.2345e-6;

                float float7 = 1.2345E6;
                float float8 = -1.2345E6;

                float float9 = 1.2345E-6;
                float float10 = -1.2345E-6;

            }
            """,
            """
            def test():
                float1 = 1.2345
                float2 = -1.2345
                float3 = 1.2345e6
                float4 = -1.2345e6
                float5 = 1.2345e-6
                float6 = -1.2345e-6
                float7 = 1.2345E6
                float8 = -1.2345E6
                float9 = 1.2345E-6
                float10 = -1.2345E-6


            """
        )

    def test_float_cast(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int var = 42;
                float foo = (float) var;

            }
            """,
            """
            def test():
                var = 42
                foo = float(var)


            """
        )

    def test_list_literals(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int foo[3] = {37, 42, 69};
                float bar[3] = {37.0, 42.0, 69.0};
            }
            """,
            """
            def test():
                foo = [37, 42, 69]
                bar = [37.0, 42.0, 69.0]


            """
        )
