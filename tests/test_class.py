from tests.utils import ConverterTestCase

from unittest import skip


class ClassTestCase(ConverterTestCase):
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

    def test_inline_multiple_constructors(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

                Foo() {
                    this->m_x = 42;
                }

                Foo(int x) {
                    this->m_x = x;
                }

                Foo(Foo& foo) {
                    this->m_x = foo.m_x;
                }
            };
            """,
            """
            class Foo:
                def __init__(self):
                    self.m_x = 42

                def __init__(self, foo):
                    self.m_x = foo.m_x

                def __init__(self, x):
                    self.m_x = x


            """,
            errors="""
            Multiple constructors for class Foo (adding ('int',))
            Multiple constructors for class Foo (adding ('Foo &',))
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

    def test_multiple_constructors(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

                Foo();
                Foo(int x);
                Foo(Foo& foo);
            };

            Foo::Foo() {
                this->m_x = 42;
            }

            Foo::Foo(int x) {
                this->m_x = x;
            }

            Foo::Foo(Foo& foo) {
                this->m_x = foo.m_x;
            }


            """,
            """
            class Foo:
                def __init__(self):
                    self.m_x = 42

                def __init__(self, foo):
                    self.m_x = foo.m_x

                def __init__(self, x):
                    self.m_x = x


            """,
            errors = """
            Multiple constructors for class Foo (adding ('int',))
            Multiple constructors for class Foo (adding ('Foo &',))
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

    def test_static_method(self):
        self.assertGeneratedOutput(
            """
            class Foo {
              public:

                static void waggle() {
                }
            };
            """,
            """
            class Foo:
                @staticmethod
                def waggle():
                    pass


            """
        )

    def test_inline_default_args(self):
        self.assertGeneratedOutput(
            """
            class Point {
              public:

                float distance(int x, int y, int z = 0) {
                    return x^2 + y^2 + z^2;
                }
            };

            void test() {
                Point *p = new Point();
                float d1 = p->distance(10, 10);
                float d2 = p->distance(5, 5, 5);
            }
            """,
            """
            class Point:
                def distance(self, x, y, z=0):
                    return x**2 + y**2 + z**2


            def test():
                p = Point()
                d1 = p.distance(10, 10)
                d2 = p.distance(5, 5, 5)


            """
        )

    def test_default_args(self):
        self.assertGeneratedOutput(
            """
            class Point {
              public:

                float distance(int x, int y, int z = 0);
            };


            float Point::distance(int x, int y, int z) {
                return x^2 + y^2 + z^2;
            }


            void test() {
                Point *p = new Point();
                float d1 = p->distance(10, 10);
                float d2 = p->distance(5, 5, 5);
            }
            """,
            """
            class Point:
                def distance(self, x, y, z=0):
                    return x**2 + y**2 + z**2


            def test():
                p = Point()
                d1 = p.distance(10, 10)
                d2 = p.distance(5, 5, 5)


            """
        )

    def test_cast(self):
        self.assertGeneratedOutput(
            """
            class Point {};

            class Point3D: public Point {};

            void test() {
                Point *var = new Point();
                const Point *cvar = new Point();
                Point3D *var3 = new Point3D();

                void *foo_cast = (void *) var;
                void *foo_static = static_cast<void *>(var);
                Point *foo_dynamic = dynamic_cast<Point *>(var3);
                void *foo_reinterpret = reinterpret_cast<void *>(var);
                Point *foo_const = const_cast<Point *>(cvar);
            }
            """,
            """
            class Point:
                pass


            class Point3D(Point):
                pass


            def test():
                var = Point()
                cvar = Point()
                var3 = Point3D()
                foo_cast = var
                foo_static = var
                foo_dynamic = var3
                foo_reinterpret = var
                foo_const = cvar


            """
        )

    def test_member_init(self):
        self.assertGeneratedOutput(
            """
            class Point {
                int origin_x;
                int origin_y;
                int origin_z;

                int m_x;
                int m_y;
                int m_z;

              public:
                Point(int x, int y, int z) :
                    origin_x(37),
                    origin_y(42),
                    origin_z(69)
                {
                    m_x = x;
                    m_y = y;
                    m_z = z;
                }
            };
            """,
            """
            class Point:
                def __init__(self, x, y, z):
                    self.origin_x = 37
                    self.origin_y = 42
                    self.origin_z = 69
                    self.m_x = x
                    self.m_y = y
                    self.m_z = z


            """
        )
