from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class IfTestCase(ConverterTestCase):
    def test_if(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10) {
                    z = 1;
                }
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    z = 1
            """
        )

    def test_empty_if(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10) {}
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    pass
            """
        )

    def test_single_statement_if(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10)
                    z = 1;
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    z = 1
            """
        )

    def test_if_else(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10) {
                    z = 1;
                } else {
                    z = 0;
                }

            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    z = 1
                else:
                    z = 0
            """
        )

    def test_empty_if_else(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10) {
                } else {
                }
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    pass
                else:
                    pass
            """
        )

    def test_single_statement_if_else(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10)
                    z = 1;
                else
                    z = 0;
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    z = 1
                else:
                    z = 0
            """
        )

    def test_if_elseif(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10) {
                    z = 1;
                } else if (x > 20) {
                    z = 2;
                }
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    z = 1
                elif x > 20:
                    z = 2
            """
        )

    def test_empty_if_elseif(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10) {
                } else if (x > 20) {
                }
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    pass
                elif x > 20:
                    pass
            """
        )

    def test_single_statement_if_elseif(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10)
                    z = 1;
                else if (x > 20)
                    z = 2;
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    z = 1
                elif x > 20:
                    z = 2
            """
        )

    def test_if_elseif_else(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10) {
                    z = 1;
                } else if (x > 20) {
                    z = 2;
                } else {
                    z = 0;
                }
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    z = 1
                elif x > 20:
                    z = 2
                else:
                    z = 0
            """
        )

    def test_empty_if_elseif_else(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10) {
                } else if (x > 20) {
                } else {
                }
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    pass
                elif x > 20:
                    pass
                else:
                    pass
            """
        )

    def test_single_statement_if_elseif_else(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10)
                    z = 1;
                else if (x > 20)
                    z = 2;
                else
                    z = 0;
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    z = 1
                elif x > 20:
                    z = 2
                else:
                    z = 0
            """
        )

    def test_if_elseif_elseif_else(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10) {
                    z = 1;
                } else if (x > 20) {
                    z = 2;
                } else if (x > 30) {
                    z = 3;
                } else {
                    z = 0;
                }
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    z = 1
                elif x > 20:
                    z = 2
                elif x > 30:
                    z = 3
                else:
                    z = 0
            """
        )

    def test_empty_if_elseif_elseif_else(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10) {
                } else if (x > 20) {
                } else if (x > 30) {
                } else {
                }
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    pass
                elif x > 20:
                    pass
                elif x > 30:
                    pass
                else:
                    pass
            """
        )

    def test_single_statement_if_elseif_elseif_else(self):
        self.assertGeneratedOutput(
            """
            void test() {
                int x = 3;
                int z;

                if (x > 10)
                    z = 1;
                else if (x > 20)
                    z = 2;
                else if (x > 30)
                    z = 3;
                else
                    z = 0;
            }

            """,
            """
            def test():
                x = 3
                if x > 10:
                    z = 1
                elif x > 20:
                    z = 2
                elif x > 30:
                    z = 3
                else:
                    z = 0
            """
        )
