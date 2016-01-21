from tests.utils import GeneratorTestCase

from unittest import skip, expectedFailure


class ClassTestCase(GeneratorTestCase):
    def test_empty_class(self):
        self.assertGeneratedOutput(
            """
            class Foo {};
            """,
            """
            class Foo:
                pass


            """
        )

    def test_empty_class_with_super(self):
        self.assertGeneratedOutput(
            """
            class Bar {};
            class Foo : public Bar {};
            """,
            """
            class Bar:
                pass


            class Foo(Bar):
                pass


            """
        )

    def test_inline_empty_constructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                Foo() {

                }
            };
            """,
            """
            class Foo:
                def __init__(self):
                    pass


            """
        )

    def test_inline_empty_constructor_with_param(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                Foo(int x) {

                }
            };
            """,
            """
            class Foo:
                def __init__(self, x):
                    pass


            """
        )

    def test_inline_constructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

                Foo(int x) {
                    this->m_x = x;
                }

            };
            """,
            """
            class Foo:
                def __init__(self, x):
                    self.m_x = x


            """
        )

    @skip("C++11 features not yet supported")
    def test_inline_initialized_field(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x = 42;

                Foo() {
                }

            };
            """,
            """
            class Foo:
                def __init__(self):
                    self.m_x = 42


            """
        )

    def test_inline_uninitialized_field(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

                Foo() {
                }

            };
            """,
            """
            class Foo:
                def __init__(self):
                    pass


            """
        )

    def test_inline_destructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

                ~Foo() {
                    this->m_x = 0;
                }

            };
            """,
            """
            class Foo:
                def __del__(self):
                    self.m_x = 0


            """
        )

    def test_inline_method(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;
                int method(int x) {
                    this->m_x = x;
                    return 42;
                }
            };
            """,
            """
            class Foo:
                def method(self, x):
                    self.m_x = x
                    return 42


            """
        )

    def test_empty_constructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                Foo();
            };

            Foo::Foo() {

            }
            """,
            """
            class Foo:
                def __init__(self):
                    pass


            """
        )

    def test_empty_constructor_with_param(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                Foo(int x);
            };

            Foo::Foo(int x) {

            }
            """,
            """
            class Foo:
                def __init__(self, x):
                    pass


            """
        )

    def test_constructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

                Foo(int x);
            };

            Foo::Foo(int x) {
                this->m_x = x;
            }
            """,
            """
            class Foo:
                def __init__(self, x):
                    self.m_x = x


            """
        )

    @skip("C++11 features not yet supported")
    def test_initialized_field(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x = 42;

                Foo();
            };

            Foo::Foo() {

            }
            """,
            """
            class Foo:
                def __init__(self):
                    self.m_x = 42


            """
        )

    def test_uninitialized_field(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

                Foo();
            };

            Foo::Foo() {
            }
            """,
            """
            class Foo:
                def __init__(self):
                    pass


            """
        )

    def test_destructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

                ~Foo();
            };

            Foo::~Foo() {
                this->m_x = 0;
            }
            """,
            """
            class Foo:
                def __del__(self):
                    self.m_x = 0


            """
        )

    def test_method(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;
                int method(int x);
            };

            int Foo::method(int x) {
                this->m_x = x;
                return 42;
            }

            """,
            """
            class Foo:
                def method(self, x):
                    self.m_x = x
                    return 42


            """
        )

    def test_virtual_method(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                virtual int method(int x) const = 0;
            };
            """,
            """
            class Foo:
                def method(self, x):
                    raise NotImplementedError()


            """
        )

    @expectedFailure
    def test_instance_argument(self):
        self.assertGeneratedOutput(
            """
            class Foo {
              public:
                int value;

                Foo(int x) {
                    value = x;
                }

                void waggle() {
                }
            };

            Foo factory(int x) {
                return Foo(x);
            }

            int fiddle(Foo in) {
                return in.value;
            }

            void test() {
                Foo obj = factory(42);

                int result = fiddle(obj);

                obj.waggle();
            }
            """,
            """
            class Foo:
                def __init__(self, x):
                    self.value = x

                def waggle(self):
                    pass


            def factory(x):
                return Foo(x)


            def fiddle(in):
                return in.value


            def test():
                obj = factory(42)
                result = fiddle(obj)
                obj.waggle()


            """
        )

    @expectedFailure
    def test_pointer_argument(self):
        self.assertGeneratedOutput(
            """
            class Foo {
              public:
                int value;

                Foo(int x) {
                    value = x;
                }

                void waggle() {
                }
            };

            Foo *factory(int x) {
                return new Foo(x);
            }


            int fiddle(Foo *in) {
                return in->value;
            }


            void test() {
                Foo* obj = factory(42);

                int result = fiddle(obj);

                obj->waggle();
            }
            """,
            """
            class Foo:
                def __init__(self, x):
                    self.value = x

                def waggle(self):
                    pass


            def factory(x):
                return Foo(x)


            def fiddle(in):
                return in.value


            def test():
                obj = factory(42)
                result = fiddle(obj)
                obj.waggle()


            """
        )

    @expectedFailure
    def test_reference_argument(self):
        self.assertGeneratedOutput(
            """
            class Foo {
              public:
                int value;

                Foo(int x) {
                    value = x;
                }

                void waggle() {
                }
            };

            Foo& factory(int x) {
                return *(new Foo(x));
            }


            int fiddle(Foo& in) {
                return in.value;
            }


            void test() {
                Foo obj = factory(42);

                int result = fiddle(obj);

                obj.waggle();
            }
            """,
            """
            class Foo:
                def __init__(self, x):
                    self.value = x

                def waggle(self):
                    pass


            def factory(x):
                return Foo(x)


            def fiddle(in):
                return in.value


            def test():
                obj = factory(42)
                result = fiddle(obj)
                obj.waggle()


            """
        )
