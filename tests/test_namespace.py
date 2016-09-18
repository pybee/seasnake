from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class NamespaceTestCase(ConverterTestCase):
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

    def test_inline_namespace(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test.cpp',
                    """
                    namespace whiz {
                        class Foo {
                          public:
                            int m_x;

                            Foo() {}

                            ~Foo() {}

                            int method(int x){
                                this->m_x = x;
                                return 42;
                            };
                        };
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
                    from test.whiz import Foo


                    def test():
                        obj = Foo()
                        obj.method(37)
                    """
                ),
                (
                    'test.whiz',
                    """
                    class Foo:
                        def __init__(self):
                            pass

                        def __del__(self):
                            pass

                        def method(self, x):
                            self.m_x = x
                            return 42
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
                            Foo();
                            ~Foo();
                            int method(int x);
                        };

                        Foo::Foo() {
                        }

                        Foo::~Foo() {
                        }

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
                    from test.whiz import Foo


                    def test():
                        obj = Foo()
                        obj.method(37)
                    """
                ),
                (
                    'test.whiz',
                    """
                    class Foo:
                        def __init__(self):
                            pass

                        def __del__(self):
                            pass

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
                    from test.whiz import Foo
                    from test.whiz.bang import Bar


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

    def test_split_namespace(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test1.cpp',
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
                    """,
                ),
                (
                    'test2.cpp',
                    """
                    namespace whiz {

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
                    """,
                )
            ],
            py=[
                (
                    'test',
                    """
                    """
                ),
                (
                    'test.whiz',
                    """
                    class Foo:
                        def method(self, x):
                            self.m_x = x
                            return 42


                    class Bar:
                        def method(self, y):
                            self.m_y = y
                            return 37
                    """
                )
            ]
        )

    def test_implied_namespace(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test.cpp',
                    """
                    namespace whiz {
                        class Foo {
                          public:
                            const static int m_x;
                        };

                        const int Foo::m_x = 1234;
                    }
                    """,
                ),
            ],
            py=[
                (
                    'test',
                    """
                    """
                ),
                (
                    'test.whiz',
                    """
                    class Foo:
                        m_x = None


                    Foo.m_x = 1234
                    """
                )
            ]
        )
        
    def test_anon_namespace(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test.cpp',
                    """
                    namespace {
                        class C{}
                    }
                    
                    void test() {
                        C c;
                    }
                    """
                )
            ],
            py=[
                (
                    'test',
                    """
                    class C:
                        pass
                    
                    
                    def test():
                        c = C()
                    """
                )
            ]
        )

    def test_using_decl(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test.cpp',
                    """
                    namespace N {
                        class C{};
                    }

                    using namespace N;

                    void test() {
                        C c = C();
                    }
                    """,
                )
            ],
            py=[
                (
                    'test',
                    """
                    from test.N import C


                    def test():
                        c = C()
                    """
                ),
                (
                    'test.N',
                    """
                    class C:
                        pass
                    """
                )
            ]
        )

    def test_using_direct_decl(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test.cpp',
                    """
                    namespace N {
                        class C{};
                    }

                    using N::C;

                    void test() {
                        C c = C();
                    }
                    """,
                )
            ],
            py=[
                (
                    'test',
                    """
                    from test.N import C


                    def test():
                        c = C()
                    """
                ),
                (
                    'test.N',
                    """
                    class C:
                        pass
                    """
                )
            ]
        )
