from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class ForTestCase(ConverterTestCase):
    def test_for(self):
        self.assertGeneratedOutput(
            """
            void test() {
                for (int i = 0; i < 15; i++) {
                }
            }

            """,
            """
            def test():
                i = 0
                while i < 15:
                    i += 1
            """
        )

    def test_for_decl_break(self):
        self.assertGeneratedOutput(
            """
            void test() {
                for (int i = 0;;) {
                    if (i == 10) {
                        break;
                    }
                    ++i;
                }
            }

            """,
            """
            def test():
                i = 0
                while True:
                    if i == 10:
                        break
                    i += 1
            """
        )

    def test_for_end_expr(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int i = 0;
                for (;;++i) {
                    if (i == 10) {
                        break;
                    }
                }
            }

            """,
            """
            def test():
                i = 0
                while True:
                    if i == 10:
                        break
                    i += 1
            """
        )

    def test_for_continue(self):
        self.assertGeneratedOutput(
            """
            void test() {
                for (int i = 0; i < 15; i++) {
                    if (i < 5) continue;
                    
                }
            }

            """,
            """
            def test():
                i = 0
                while i < 15:
                    if i < 5:
                        i += 1
                        continue
                    i += 1
            """
        )

    def test_empty_for1(self):
        self.assertGeneratedOutput(
            """
            void test() {
                for (;;);
            }

            """,
            """
            def test():
                while True:
                    pass
            """
        )

    def test_empty_for2(self):
        self.assertGeneratedOutput(
            """
            void test() {
                for (;;) {}
            }

            """,
            """
            def test():
                while True:
                    pass
            """
        )
