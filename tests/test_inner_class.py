from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class InnerClassTestCase(ConverterTestCase):
    def test_simple(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test.cpp',
                    """
                    namespace bar {
                        namespace foo {
                            class Outer {
                                int m_x;
                              public:
                                Outer(int extra) {}

                                class Inner {
                                    int m_y;
                                  public:
                                    Inner(int extra) {}
                                };
                            };
                        }
                    }

                    void test() {
                        bar::foo::Outer *obj1 = new bar::foo::Outer(37);
                        bar::foo::Outer::Inner *obj2 = new bar::foo::Outer::Inner(42);
                    }
                    """,
                )
            ],
            py=[
                (
                    'test',
                    """
                    from test.bar.foo import Outer


                    def test():
                        obj1 = Outer(37)
                        obj2 = Outer.Inner(42)
                    """
                ),
                (
                    'test.bar',
                    """
                    """
                ),
                (
                    'test.bar.foo',
                    """
                    class Outer:
                        def __init__(self, extra):
                            pass

                        class Inner:
                            def __init__(self, extra):
                                pass
                    """
                )
            ]
        )

    def test_inline_class(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test.cpp',
                    """
                    namespace bar {
                        namespace foo {
                            class Outer {
                                int m_x;
                              public:
                                Outer(int extra) {
                                    m_x = 42 + extra;
                                }

                                ~Outer() {

                                }

                                void outer_method() {
                                    m_x *= 2;
                                }

                                class Inner {
                                    int m_y;
                                  public:
                                    Inner(int extra) {
                                        m_y = 37 - extra;
                                    }

                                    ~Inner() {

                                    }

                                    void inner_method() {
                                        m_y /= 2;
                                    }

                                    Outer *ref_method(Outer *in) {
                                        return in;
                                    }
                                };
                            };
                        }
                    }

                    void test() {
                        bar::foo::Outer *obj1 = new bar::foo::Outer(37);
                        bar::foo::Outer::Inner *obj2 = new bar::foo::Outer::Inner(42);

                        obj1->outer_method();
                        obj2->inner_method();
                    }
                    """,
                )
            ],
            py=[
                (
                    'test',
                    """
                    from test.bar.foo import Outer


                    def test():
                        obj1 = Outer(37)
                        obj2 = Outer.Inner(42)
                        obj1.outer_method()
                        obj2.inner_method()
                    """
                ),
                (
                    'test.bar',
                    """
                    """
                ),
                (
                    'test.bar.foo',
                    """
                    class Outer:
                        def __init__(self, extra):
                            self.m_x = 42 + extra

                        def __del__(self):
                            pass

                        class Inner:
                            def __init__(self, extra):
                                self.m_y = 37 - extra

                            def __del__(self):
                                pass

                            def inner_method(self):
                                self.m_y /= 2

                            def ref_method(self, in):
                                return in

                        def outer_method(self):
                            self.m_x *= 2
                    """
                )
            ]
        )

    def test_class(self):
        self.assertMultifileGeneratedOutput(
            cpp=[
                (
                    'test.cpp',
                    """
                    namespace bar {
                        namespace foo {
                            class Outer {
                                int m_x;
                              public:
                                Outer(int extra);
                                ~Outer();

                                void outer_method();

                                class Inner {
                                    int m_y;
                                  public:
                                    Inner(int extra);
                                    ~Inner();

                                    void inner_method();

                                    Outer *ref_method(Outer *in);
                                };
                            };

                            Outer::Outer(int extra) {
                                m_x = 42 + extra;
                            }

                            Outer::~Outer() {
                            }

                            void Outer::outer_method() {
                                m_x *= 2;
                            }

                            Outer::Inner::Inner(int extra) {
                                m_y = 37 - extra;
                            }

                            Outer::Inner::~Inner() {
                            }

                            void Outer::Inner::inner_method() {
                                m_y /= 2;
                            }

                            Outer *Outer::Inner::ref_method(Outer *in) {
                                return in;
                            }
                        }
                    }

                    void test() {
                        bar::foo::Outer *obj1 = new bar::foo::Outer(37);
                        bar::foo::Outer::Inner *obj2 = new bar::foo::Outer::Inner(42);

                        obj1->outer_method();
                        obj2->inner_method();
                    }
                    """,
                )
            ],
            py=[
                (
                    'test',
                    """
                    from test.bar.foo import Outer


                    def test():
                        obj1 = Outer(37)
                        obj2 = Outer.Inner(42)
                        obj1.outer_method()
                        obj2.inner_method()
                    """
                ),
                (
                    'test.bar',
                    """
                    """
                ),
                (
                    'test.bar.foo',
                    """
                    class Outer:
                        def __init__(self, extra):
                            self.m_x = 42 + extra

                        def __del__(self):
                            pass

                        class Inner:
                            def __init__(self, extra):
                                self.m_y = 37 - extra

                            def __del__(self):
                                pass

                            def inner_method(self):
                                self.m_y /= 2

                            def ref_method(self, in):
                                return in

                        def outer_method(self):
                            self.m_x *= 2
                    """
                )
            ]
        )
