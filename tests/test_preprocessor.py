from io import StringIO
from unittest import TestCase

from tests.utils import adjust
from seasnake.preprocessor import preprocess


class PreprocessorTestCase(TestCase):
    def assertPreprocessor(self, input, output, errors=None, **options):
        stderr = StringIO()
        processed = preprocess(adjust(input), filename=None, errors=stderr, **options)
        self.assertEqual(processed, adjust(output))
        if errors:
            self.assertEqual(stderr.getvalue(), adjust(errors))
        else:
            self.assertEqual(stderr.getvalue(), '')


class IncludeTestCase(PreprocessorTestCase):
    def test_include(self):
        self.assertPreprocessor(
            """
            #include <foo.h>

            Hello.

            """,
            """


            Hello.
            """
        )

    def test_include_quoted(self):
        self.assertPreprocessor(
            """
            #include "foo.h"

            Hello.

            """,
            """


            Hello.
            """
        )


class DefineTestCase(PreprocessorTestCase):
    def test_simple_define(self):
        self.assertPreprocessor(
            """
            #define FOO world

            Hello, FOO.

            """,
            """


            Hello, world.
            """
        )

    def test_external_define(self):
        self.assertPreprocessor(
            """
            Hello, FOO.

            """,
            """
            Hello, world.
            """,
            defines={
                'FOO': 'world'
            }
        )


class IfDefTestCase(PreprocessorTestCase):
    def test_undefined(self):
        self.assertPreprocessor(
            """
            #ifdef FOO
            Hello.
            #endifdef
            """,
            """

            """
        )

    def test_defined(self):
        self.assertPreprocessor(
            """
            #define FOO
            #ifdef FOO
            Hello.
            #endifdef
            """,
            """


            Hello.
            """
        )

    def test_defined_externally(self):
        self.assertPreprocessor(
            """
            #ifdef FOO
            Hello.
            #endifdef
            """,
            """

            Hello.
            """,
            defines={
                'FOO': '1'
            }
        )


class IfNDefTestCase(PreprocessorTestCase):
    def test_undefined(self):
        self.assertPreprocessor(
            """
            #ifndef FOO
            Hello.
            #endifdnef
            """,
            """

            Hello.
            """
        )

    def test_defined(self):
        self.assertPreprocessor(
            """
            #define FOO
            #ifndef FOO
            Hello.
            #endifndef
            """,
            """


            """
        )

    def test_defined_externally(self):
        self.assertPreprocessor(
            """
            #ifndef FOO
            Hello.
            #endifndef
            """,
            """

            """,
            defines={
                'FOO': '1'
            }
        )


class IfTestCase(PreprocessorTestCase):
    def test_undefined(self):
        self.assertPreprocessor(
            """
            #if FOO
            Hello.
            #endif
            """,
            """

            """,
            errors="""
            :1 Couldn't evaluate expression
            """
        )

    def test_defined_empty(self):
        self.assertPreprocessor(
            """
            #define FOO
            #if FOO
            Hello.
            #endif
            """,
            """


            """,
            errors="""
            :None Couldn't evaluate expression
            """
        )

    def test_defined_false(self):
        self.assertPreprocessor(
            """
            #define FOO 0
            #if FOO
            Hello.
            #endif
            """,
            """


            """
        )

    def test_defined_true(self):
        self.assertPreprocessor(
            """
            #define FOO 1
            #if FOO
            Hello.
            #endif
            """,
            """


            Hello.
            """
        )

    def test_defined_false_externally(self):
        self.assertPreprocessor(
            """
            #if FOO
            Hello.
            #endifdef
            """,
            """

            """,
            defines={
                'FOO': '0'
            }
        )

    def test_defined_true_externally(self):
        self.assertPreprocessor(
            """
            #if FOO
            Hello.
            #endifdef
            """,
            """

            Hello.
            """,
            defines={
                'FOO': '1'
            }
        )

    def test_defined_false_with_else(self):
        self.assertPreprocessor(
            """
            #define FOO 0
            #if FOO
            Hello.
            #else
            Goodbye.
            #endif
            """,
            """



            Goodbye.
            """
        )

    def test_defined_true_with_else(self):
        self.assertPreprocessor(
            """
            #define FOO 1
            #if FOO
            Hello.
            #else
            Goodbye.
            #endif
            """,
            """


            Hello.

            """
        )
