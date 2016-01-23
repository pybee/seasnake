from tests.utils import GeneratorTestCase


class NamespaceTestCase(GeneratorTestCase):
    def test_empty_namespace(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test.cpp',
                    """
                    namespace whiz {}
                    """
                )
            ],
            py=[
                (
                    'test',
                    """
                    """
                )
            ]
        )

    def test_namespace(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test.cpp',
                    """
                    namespace whiz {
                        class Foo {
                          public:
                            int m_x;
                            int method(int x);
                        };

                        int Foo::method(int x) {
                            this->m_x = x;
                            return 42;
                        }
                    }

                    void test() {
                        whiz::Foo *obj = new whiz::Foo();
                        obj->method(37);
                    }
                    """,
                )
            ],
            py=[
                (
                    'test',
                    """
                    from whiz import Foo


                    def test():
                        obj = Foo()
                        obj.method(37)


                    """
                ),
                (
                    'test.whiz',
                    """
                    class Foo:
                        def method(self, x):
                            self.m_x = x
                            return 42


                    """
                )
            ]
        )

    def test_deep_namespace(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test.cpp',
                    """
                    namespace whiz {
                        class Foo {
                          public:
                            int m_x;
                            int method(int x);
                        };

                        int Foo::method(int x) {
                            this->m_x = x;
                            return 42;
                        }

                        namespace bang {

                            class Bar {
                              public:
                                int m_y;
                                int method(int y);
                            };

                            int Bar::method(int y) {
                                this->m_y = y;
                                return 37;
                            }
                        }
                    }

                    void test() {
                        whiz::Foo *obj1 = new whiz::Foo();
                        whiz::bang::Bar *obj2 = new whiz::bang::Bar();
                        obj1->method(37);
                        obj2->method(42);
                    }
                    """,
                )
            ],
            py=[
                (
                    'test',
                    """
                    from whiz import Foo
                    from whiz.bang import Bar


                    def test():
                        obj1 = Foo()
                        obj2 = Bar()
                        obj1.method(37)
                        obj2.method(42)


                    """
                ),
                (
                    'test.whiz',
                    """
                    class Foo:
                        def method(self, x):
                            self.m_x = x
                            return 42


                    """
                ),
                (
                    'test.whiz.bang',
                    """
                    class Bar:
                        def method(self, y):
                            self.m_y = y
                            return 37


                    """
                )
            ]
        )
