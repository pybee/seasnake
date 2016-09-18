from __future__ import unicode_literals

from tests.utils import ConverterTestCase

from unittest import skip


class ClassTestCase(ConverterTestCase):
    def test_empty_class(self):
        self.assertGeneratedOutput(
            """
            class Foo {};

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

    def test_empty_class_with_super(self):
        self.assertGeneratedOutput(
            """
            class Bar {};
            class Foo : public Bar {};

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();
            }
            """,
            """
            class Bar:
                pass


            class Foo(Bar):
                pass


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )

    def test_inline_empty_constructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
              public:
                Foo() {

                }
            };

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();
            }
            """,
            """
            class Foo:
                def __init__(self):
                    pass


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )

    def test_inline_empty_constructor_with_param(self):
        self.assertGeneratedOutput(
            """
            class Foo {
              public:
                Foo(int x) {

                }
            };

            void test() {
                Foo f1 = Foo(37);
                Foo *f2 = new Foo(42);
            }
            """,
            """
            class Foo:
                def __init__(self, x):
                    pass


            def test():
                f1 = Foo(37)
                f2 = Foo(42)
           """
        )

    def test_inline_constructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;
              public:
                Foo(int x) {
                    this->m_x = x;
                }
            };

            void test() {
                Foo f1 = Foo(37);
                Foo *f2 = new Foo(42);
            }
            """,
            """
            class Foo:
                def __init__(self, x):
                    self.m_x = x


            def test():
                f1 = Foo(37)
                f2 = Foo(42)
            """
        )

    def test_inline_multiple_constructors(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;
              public:
                Foo() {
                    this->m_x = 42;
                }

                Foo(int x) {
                    this->m_x = x;
                }

                Foo(const Foo& foo) {
                    this->m_x = foo.m_x;
                }
            };

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();

                Foo f3 = Foo(37);
                Foo *f4 = new Foo(42);

                Foo f5 = Foo(f1);
                Foo *f6 = new Foo(*f2);
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


            def test():
                f1 = Foo()
                f2 = Foo()
                f3 = Foo(37)
                f4 = Foo(42)
                f5 = Foo(f1)
                f6 = Foo(f2)
            """,
            errors="""
            Multiple constructors for class Foo (adding [int])
            Multiple constructors for class Foo (adding [const Foo &])
            """
        )

    def test_inline_constructor_default_args(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;

              public:
                Foo(int x=10) {
                    this->m_x = x;
                }
            };

            void test() {
                Foo f1 = Foo(37);
                Foo *f2 = new Foo(42);
            }
            """,
            """
            class Foo:
                def __init__(self, x=10):
                    self.m_x = x


            def test():
                f1 = Foo(37)
                f2 = Foo(42)
            """
        )

    @skip("C++11 features not yet supported")
    def test_inline_initialized_field(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x = 42;

              public:
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

              public:
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

              public:
                ~Foo() {
                    this->m_x = 0;
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
                def __del__(self):
                    self.m_x = 0


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )

    def test_inline_method(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;
              public:
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
              public:
                Foo();
            };

            Foo::Foo() {

            }

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();
            }
            """,
            """
            class Foo:
                def __init__(self):
                    pass


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )

    def test_empty_constructor_with_param(self):
        self.assertGeneratedOutput(
            """
            class Foo {
              public:
                Foo(int x);
            };

            Foo::Foo(int x) {

            }

            void test() {
                Foo f1 = Foo(37);
                Foo *f2 = new Foo(42);
            }
            """,
            """
            class Foo:
                def __init__(self, x):
                    pass


            def test():
                f1 = Foo(37)
                f2 = Foo(42)
            """
        )

    def test_constructor(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;
              public:
                Foo(int arg);
            };

            Foo::Foo(int x) {
                this->m_x = x;
            }

            void test() {
                Foo f1 = Foo(37);
                Foo *f2 = new Foo(42);
            }
            """,
            """
            class Foo:
                def __init__(self, x):
                    self.m_x = x


            def test():
                f1 = Foo(37)
                f2 = Foo(42)
            """
        )

    def test_multiple_constructors(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;
              public:
                Foo();
                Foo(int x);
                Foo(const Foo& foo);
            };

            Foo::Foo() {
                this->m_x = 42;
            }

            Foo::Foo(int x) {
                this->m_x = x;
            }

            Foo::Foo(const Foo& foo) {
                this->m_x = foo.m_x;
            }

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();

                Foo f3 = Foo(37);
                Foo *f4 = new Foo(42);

                Foo f5 = Foo(f1);
                Foo *f6 = new Foo(*f2);
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


            def test():
                f1 = Foo()
                f2 = Foo()
                f3 = Foo(37)
                f4 = Foo(42)
                f5 = Foo(f1)
                f6 = Foo(f2)
            """,
            errors="""
            Multiple constructors for class Foo (adding [int])
            Multiple constructors for class Foo (adding [const Foo &])
            """
        )

    def test_constructor_default_args(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;
              public:
                Foo(int arg=10);
            };

            Foo::Foo(int x) {
                this->m_x = x;
            }

            void test() {
                Foo f1 = Foo(37);
                Foo *f2 = new Foo(42);
            }
            """,
            """
            class Foo:
                def __init__(self, x=10):
                    self.m_x = x


            def test():
                f1 = Foo(37)
                f2 = Foo(42)
            """
        )

    @skip("C++11 features not yet supported")
    def test_initialized_field(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x = 42;
              public:
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
              public:
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
              public:
                ~Foo();
            };

            Foo::~Foo() {
                this->m_x = 0;
            }

            void test() {
                Foo f1 = Foo();
                Foo *f2 = new Foo();

                delete f2;
            }
            """,
            """
            class Foo:
                def __del__(self):
                    self.m_x = 0


            def test():
                f1 = Foo()
                f2 = Foo()
            """
        )

    def test_method(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                int m_x;
              public:
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
              public:
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
              public:
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
              public:
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
              public:
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

    def test_inline_static_method(self):
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

    def test_static_method(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                float x;
                float y;

                static void waggle();
            };

            void Foo::waggle() {
            }
            """,
            """
            class Foo:
                @staticmethod
                def waggle():
                    pass
            """
        )

    def test_inline_static_field(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                float x;
                float y;
                constexpr static float range = 10.0;
            };
            """,
            """
            class Foo:
                range = 10.0
            """
        )

    def test_static_field(self):
        self.assertGeneratedOutput(
            """
            class Foo {
                float x;
                float y;
                const static float range;
            };

            const float Foo::range = 10.0;
            """,
            """
            class Foo:
                range = None


            Foo.range = 10.0
            """
        )

    def test_inline_default_args(self):
        self.assertGeneratedOutput(
            """
            class Point {
              public:
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
            class Point {
              public:
                float distance(int x, int y, int z = 0);
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
                def distance(self, x, y, z=0):
                    return x * x + y * y + z * z


            def test():
                p = Point()
                d1 = p.distance(10, 10)
                d2 = p.distance(5, 5, 5)
            """
        )

    def test_inline_default_attribute_args(self):
        self.assertGeneratedOutput(
            """
            struct Temperature {
                static const int HOT = 1;
                static const int COLD = 0;
            };

            class Point {
              public:
                float distance(int x, int y, int temp=Temperature::HOT) {
                    return x * x + y * y;
                }
            };

            void test() {
                Point *p = new Point();
                float d1 = p->distance(10, 10);
                float d2 = p->distance(5, 5, 5);
            }
            """,
            """
            class Temperature:
                HOT = 1
                COLD = 0


            class Point:
                def distance(self, x, y, temp=Temperature.HOT):
                    return x * x + y * y


            def test():
                p = Point()
                d1 = p.distance(10, 10)
                d2 = p.distance(5, 5, 5)
            """
        )

    def test_default_attribute_args(self):
        self.assertGeneratedOutput(
            """
            struct Temperature {
                static const int HOT = 1;
                static const int COLD = 0;
            };

            class Point {
              public:

                float distance(int x, int y, int temp=Temperature::HOT);
            };


            float Point::distance(int x, int y, int temp) {
                return x * x + y * y;
            }


            void test() {
                Point *p = new Point();
                float d1 = p->distance(10, 10);
                float d2 = p->distance(5, 5, 5);
            }
            """,
            """
            class Temperature:
                HOT = 1
                COLD = 0


            class Point:
                def distance(self, x, y, temp=Temperature.HOT):
                    return x * x + y * y


            def test():
                p = Point()
                d1 = p.distance(10, 10)
                d2 = p.distance(5, 5, 5)
            """
        )

    def test_prototype_without_arg_names(self):
        self.assertGeneratedOutput(
            """
            class Point {
              public:

                float distance(int, int, int);
            };


            float Point::distance(int x, int y, int z) {
                return x * x + y * y + z * z;
            }
            """,
            """
            class Point:
                def distance(self, x, y, z):
                    return x * x + y * y + z * z
            """
        )

    def test_prototype_with_different_arg_names(self):
        self.assertGeneratedOutput(
            """
            class Point {
              public:

                float distance(int x_coord, int y_coord, int z_coord);
            };


            float Point::distance(int x, int y, int z) {
                return x * x + y * y + z * z;
            }
            """,
            """
            class Point:
                def distance(self, x, y, z):
                    return x * x + y * y + z * z
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

    def test_inner_enum(self):
        self.assertGeneratedOutput(
            """
            class Point {
                enum Temperature {
                    HOT,
                    COLD
                };
            };
            """,
            """
            from enum import Enum


            class Point:
                class Temperature(Enum):
                    HOT = 0
                    COLD = 1
            """
        )

    def test_forward_declaration(self):
        self.assertGeneratedOutput(
            """
            class Point {
                void measure() {
                    if (temp == HOT) {
                        m_size = 10;
                    } else {
                        m_size = 5;
                    }
                }

                int m_size;

                enum Temperature {
                    HOT,
                    COLD
                };

                Temperature temp;
            };
            """,
            """
            from enum import Enum


            class Point:
                class Temperature(Enum):
                    HOT = 0
                    COLD = 1

                def measure(self):
                    if self.temp == Point.Temperature.HOT:
                        self.m_size = 10
                    else:
                        self.m_size = 5
            """
        )

    def test_override(self):
        self.assertGeneratedOutput(
            """
            class Point {
                virtual void ping() {
                }
            };

            class Point3D : public Point {
                virtual void ping() override {
                }
            };
            """,
            """
            class Point:
                def ping(self):
                    pass


            class Point3D(Point):
                def ping(self):
                    pass
            """
        )

    def test_final(self):
        self.assertGeneratedOutput(
            """
            class Point {
                virtual void ping() {
                }
            };

            class Point3D : public Point {
                virtual void ping() final {
                }
            };
            """,
            """
            class Point:
                def ping(self):
                    pass


            class Point3D(Point):
                def ping(self):
                    pass
            """
        )

    def test_override_final(self):
        self.assertGeneratedOutput(
            """
            class Point {
                virtual void ping() {
                }
            };

            class Point3D : public Point {
                virtual void ping() override final {
                }
            };
            """,
            """
            class Point:
                def ping(self):
                    pass


            class Point3D(Point):
                def ping(self):
                    pass
            """
        )

    def test_final_override(self):
        self.assertGeneratedOutput(
            """
            class Point {
                virtual void ping() {
                }
            };

            class Point3D : public Point {
                virtual void ping() final override {
                }
            };
            """,
            """
            class Point:
                def ping(self):
                    pass


            class Point3D(Point):
                def ping(self):
                    pass
            """
        )

    def test_predeclaration(self):
        self.assertGeneratedOutput(
            """
            class Point {
              public:
                void ping() {
                }
            };

            class Point;

            void test() {
                Point *p = new Point();

                p->ping();
            }

            """,
            """
            class Point:
                def ping(self):
                    pass


            def test():
                p = Point()
                p.ping()
            """
        )

    def test_attributes_visible_on_subclass(self):
        self.assertGeneratedOutput(
            """
            class Bar {
              protected:
                enum Temperature {
                    COLD,
                    HOT,
                };

                int m_x;


            };

            class Foo : public Bar {
                void fiddle(Temperature temp=HOT) {
                    if (temp == COLD) {
                        m_x = 10;
                    } else {
                        m_x = 100;
                    }
                }
            };
            """,
            """
            from enum import Enum


            class Bar:
                class Temperature(Enum):
                    COLD = 0
                    HOT = 1


            class Foo(Bar):
                def fiddle(self, temp=Bar.Temperature.HOT):
                    if temp == Bar.Temperature.COLD:
                        self.m_x = 10
                    else:
                        self.m_x = 100
            """
        )
        
    def test_template_param(self):
        self.assertGeneratedOutput(
            """
            template <typename T>
            class C {};
            
            class Test {
                void fn(C<int> p);
            }
        
            """,
            """
            class C:
                pass
            
            
            class Test:
                def fn(self, p):
                    pass
            """
        )
        
    def test_template2_param(self):
        self.assertGeneratedOutput(
            """
            template <typename T>
            class C1 {};
            
            template <typename T>
            class C2 {};
            
            class Test {
                void fn(C1<C2<int>> p);
            }
        
            """,
            """
            class C1:
                pass
            
            
            class C2:
                pass
            
            
            class Test:
                def fn(self, p):
                    pass
            """
        )
        
    def test_template_return(self):
        self.assertGeneratedOutput(
            """
            template <typename T>
            class C {};
            
            class Test {
                C<int> void fn();
            }
        
            """,
            """
            class C:
                pass
            
            
            class Test:
                def fn(self):
                    pass
            """
        )
        
    def test_template2_return(self):
        self.assertGeneratedOutput(
            """
            template <typename T>
            class C1 {};
            
            template <typename T>
            class C2 {};
            
            class Test {
                C1<C2<int>> fn();
            }
        
            """,
            """
            class C1:
                pass
            
            
            class C2:
                pass
            
            
            class Test:
                def fn(self):
                    pass
            """
        )
        
    def test_template_ns_param(self):
        self.assertGeneratedOutput(
            """
            namespace N {
                template <typename T>
                class C {};
            }
            
            class Test {
                void fn(N::C<int> p);
            }
            """,
            """
            class Test:
                def fn(self, p):
                    pass
            """
        )
        
    def test_template_ns_return(self):
        self.assertGeneratedOutput(
            """
            namespace N {
                template <typename T>
                class C {};
            }
            
            class Test {
                N::C<int> fn();
            }
            """,
            """
            class Test:
                def fn(self):
                    pass
            """
        )
        
    def test_template2_ns_param(self):
        self.assertGeneratedOutput(
            """
            namespace N {
                template <typename T>
                class C1 {};
                
                template <typename T>
                class C2 {};
            }
            
            class Test {
                N::C1<N::C2<int>> fn(N::C1<N::C2<int>> p);
            }
        
            """,
            """
            class Test:
                def fn(self, p):
                    pass
            """
        )
        
