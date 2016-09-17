from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class DoWhileTestCase(ConverterTestCase):
    def test_do(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                
                do {
                    x = x - 1;
                } while (x != 0);
            }

            """,
            """
            def test():
                x = 3
                while True:
                    x = x - 1
                    if not (x != 0):
                        break
            """
        )

    def test_empty_do(self):
        self.assertGeneratedOutput(
            """
            void test() {
                do {} while (true);
            }

            """,
            """
            def test():
                while True:
                    if not (True):
                        break
            """
        )

    def test_do_break(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                
                do {
                    x = x - 1;
                    if (x == 0) 
                        break;
                } while (true);
            }

            """,
            """
            def test():
                x = 3
                while True:
                    x = x - 1
                    if x == 0:
                        break
                    if not (True):
                        break
            """
        )

    def test_do_continue(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                
                do {
                    x = x - 1;
                    if (x != 0) 
                        continue;
                } while (false);
            }

            """,
            """
            def test():
                x = 3
                while True:
                    x = x - 1
                    if x != 0:
                        continue
                    if not (False):
                        break
            """
        )

    def test_while(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                
                while (x != 0) {
                    x = x - 1;
                }
            }

            """,
            """
            def test():
                x = 3
                while x != 0:
                    x = x - 1
            """
        )

    def test_while_break(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                
                while (true) {
                    x = x - 1;
                    if (x == 0) 
                        break;
                }
            }

            """,
            """
            def test():
                x = 3
                while True:
                    x = x - 1
                    if x == 0:
                        break
            """
        )
        
    def test_while_continue(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                
                while (true) {
                    x = x - 1;
                    if (x != 0) 
                        continue;
                }
            }

            """,
            """
            def test():
                x = 3
                while True:
                    x = x - 1
                    if x != 0:
                        continue
            """
        )

    def test_empty_while1(self):
        self.assertGeneratedOutput(
            """
            void test() {
                while (true);
            }

            """,
            """
            def test():
                while True:
                    pass
            """
        )

    def test_empty_while2(self):
        self.assertGeneratedOutput(
            """
            void test() {
                while (true) {}
            }

            """,
            """
            def test():
                while True:
                    pass
            """
        )
