from __future__ import unicode_literals

from tests.utils import ConverterTestCase

from unittest import skip


class StructTestCase(ConverterTestCase):
    def test_empty_struct(self):
        self.assertGeneratedOutput(
            """
            struct Foo {};

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();
            }
            """,
            """
            class Foo:
                pass


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )

    def test_simple_struct(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
                float x;
                float y;
            };

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();
            }
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )

    def test_inline_destructor(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
                float x;
                float y;

                ~Foo() {
                    this->x = 0;
                }
            };

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();

                delete f2;
            }
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y

                def __del__(self):
                    self.x = 0


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )

    def test_inline_method(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
                float x;
                float y;

                int method(int x) {
                    this->x = x;
                    return 42;
                }
            };
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y

                def method(self, x):
                    self.x = x
                    return 42
            """
        )

    def test_destructor(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
                float x;
                float y;


                ~Foo();
            };

            Foo::~Foo() {
                this->x = 0;
            }

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();

                delete f2;
            }
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y

                def __del__(self):
                    self.x = 0


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )

    def test_method(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
                float x;
                float y;

                int method(int x);
            };

            int Foo::method(int x) {
                this->x = x;
                return 42;
            }

            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y

                def method(self, x):
                    self.x = x
                    return 42
            """
        )

    def test_virtual_method(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
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
            struct Foo {
                int value;

                void waggle() {
                }
            };

            Foo factory(int x) {
                return Foo();
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
                def __init__(self, value=None):
                    self.value = value

                def waggle(self):
                    pass


            def factory(x):
                return Foo()


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
            struct Foo {
                int value;

                void waggle() {
                }
            };

            Foo *factory(int x) {
                return new Foo();
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
                def __init__(self, value=None):
                    self.value = value

                def waggle(self):
                    pass


            def factory(x):
                return Foo()


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
            struct Foo {
                int value;

                void waggle() {
                }
            };

            Foo& factory(int x) {
                return *(new Foo());
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
                def __init__(self, value=None):
                    self.value = value

                def waggle(self):
                    pass


            def factory(x):
                return Foo()


            def fiddle(in):
                return in.value


            def test():
                obj = factory(42)
                result = fiddle(obj)
                obj.waggle()
            """
        )

    def test_inline_static_method(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
                float x;
                float y;

                static void waggle() {
                }
            };
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y

                @staticmethod
                def waggle():
                    pass
            """
        )

    def test_static_method(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
                float x;
                float y;

                static void waggle();
            };

            void Foo::waggle() {
            }
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y

                @staticmethod
                def waggle():
                    pass
            """
        )

    def test_inline_static_field(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
                float x;
                float y;
                constexpr static float range = 10.0;
            };
            """,
            """
            class Foo:
                range = 10.0

                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y
            """
        )

    def test_static_field(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
                float x;
                float y;
                const static float range;
            };

            const float Foo::range = 10.0;
            """,
            """
            class Foo:
                range = None

                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y


            Foo.range = 10.0
            """
        )

    def test_inline_default_args(self):
        self.assertGeneratedOutput(
            """
            struct Point {
                float x;
                float y;

                float distance(int x, int y, int z = 0) {
                    return x * x + y * y + z * z;
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
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y

                def distance(self, x, y, z=0):
                    return x * x + y * y + z * z


            def test():
                p = Point()
                d1 = p.distance(10, 10)
                d2 = p.distance(5, 5, 5)
            """
        )

    def test_default_args(self):
        self.assertGeneratedOutput(
            """
            struct Point {
                float x;
                float y;

                float distance(int x, int y, int z=0);
            };


            float Point::distance(int x, int y, int z) {
                return x * x + y * y + z * z;
            }


            void test() {
                Point *p = new Point();
                float d1 = p->distance(10, 10);
                float d2 = p->distance(5, 5, 5);
            }
            """,
            """
            class Point:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y

                def distance(self, x, y, z=0):
                    return x * x + y * y + z * z


            def test():
                p = Point()
                d1 = p.distance(10, 10)
                d2 = p.distance(5, 5, 5)
            """
        )

    def test_cast(self):
        self.assertGeneratedOutput(
            """
            struct Point {};

            struct Point3D: public Point {};

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

    def test_list_instantiation(self):
        self.assertGeneratedOutput(
            """
            struct Point {
                int x;
                int y;
                int z;
            };

            void test() {
                Point var = {37, 42, 69};
            }
            """,
            """
            class Point:
                def __init__(self, x=None, y=None, z=None):
                    self.x = x
                    self.y = y
                    self.z = z


            def test():
                var = Point(37, 42, 69)
            """
        )

    def test_predeclaration(self):
        self.assertGeneratedOutput(
            """
            struct Foo {
                float x;
                float y;
            };

            struct Foo;

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();
            }
            """,
            """
            class Foo:
                def __init__(self, x=None, y=None):
                    self.x = x
                    self.y = y


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )
