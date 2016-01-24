from tests.utils import ConverterTestCase


class PreprocessorTestCase(ConverterTestCase):
    def test_explitit_enable(self):
        self.assertGeneratedOutput(
            """
            #if LARGE
            int value = 100;
            #else
            int value = 2;
            #endif
            """,
            """
            value = 100
            """,
            flags=[
                '-DLARGE=1'
            ]
        )

    def test_explicit_disable(self):
        self.assertGeneratedOutput(
            """
            #if LARGE
            int value = 100;
            #else
            int value = 2;
            #endif
            """,
            """
            value = 2
            """,
            flags=[
                '-DLARGE=0'
            ]
        )

    def test_implicit_disable(self):
        self.assertGeneratedOutput(
            """
            #if LARGE
            int value = 100;
            #else
            int value = 2;
            #endif
            """,
            """
            value = 2
            """,
            flags=[
            ]
        )

    def test_content(self):
        self.assertGeneratedOutput(
            """
            int value = VALUE;
            """,
            """
            value = 3742
            """,
            flags=[
                '-DVALUE=3742'
            ]
        )
