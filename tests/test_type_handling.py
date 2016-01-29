from __future__ import unicode_literals

from tests.utils import ConverterTestCase


class TypeReferencingCases:
    #######################################################################
    # This base class defined a spanning set of type referencing cases.
    # By subclassing and providing a template, a wide range of referencing
    # interactions can be tested.
    #######################################################################
    # Primitive type
    def test_primitive(self):
        self.assert_example(data='int', usage='int', result='int', value='42', arg='val', py_value='42')

    def test_primitive_ref(self):
        self.assert_example(data='int', usage='int&', result='int', value='42', arg='val', py_value='42')

    def test_primitive_pointer(self):
        self.assert_example(data='int', usage='int*', result='int*', value='42', arg='&val', py_value='42')

    def test_primitive_multi_pointer(self):
        self.assert_example(data='int*', usage='int**', result='int**', value='0', arg='&val', py_value='0')

    #----------------------------------------------------------------------
    # Explicitly referenced enum in the same namespace
    def test_same_ns_explicit_enum(self):
        self.assert_example(data='C::D::F', usage='C::D::F', result='C::D::F', value='C::D::N', arg='val', imports=('F',), py_value='F.N')

    def test_same_ns_explicit_enum_ref(self):
        self.assert_example(data='C::D::F', usage='C::D::F&', result='C::D::F', value='C::D::N', arg='val', imports=('F',), py_value='F.N')

    def test_same_ns_explicit_enum_pointer(self):
        self.assert_example(data='C::D::F', usage='C::D::F*', result='C::D::F*', value='C::D::N', arg='&val', imports=('F',), py_value='F.N')

    def test_same_ns_explicit_enum_multi_pointer(self):
        self.assert_example(data='C::D::F*', usage='C::D::F**', result='C::D::F**', value='0', arg='&val', py_value='0')

    #----------------------------------------------------------------------
    # Implicitly referenced enum in the same namespace
    def test_same_ns_implicit_enum(self):
        self.assert_example(data='C::D::F', usage='F', result='C::D::F', value='C::D::N', arg='val', imports=('F',), py_value='F.N')

    def test_same_ns_implicit_enum_ref(self):
        self.assert_example(data='C::D::F', usage='F&', result='C::D::F', value='C::D::N', arg='val', imports=('F',), py_value='F.N')

    def test_same_ns_implicit_enum_pointer(self):
        self.assert_example(data='C::D::F', usage='F*', result='C::D::F*', value='C::D::N', arg='&val', imports=('F',), py_value='F.N')

    def test_same_ns_implicit_enum_multi_pointer(self):
        self.assert_example(data='C::D::F*', usage='F**', result='C::D::F**', value='0', arg='&val', py_value='0')

    #----------------------------------------------------------------------
    # Enum from a different namespace
    def test_other_ns_enum(self):
        self.assert_example(data='A::B::E', usage='A::B::E', result='A::B::E', value='A::B::P', arg='val', imports=('E',), py_value='E.P')

    def test_other_ns_enum_ref(self):
        self.assert_example(data='A::B::E', usage='A::B::E&', result='A::B::E', value='A::B::P', arg='val', imports=('E',), py_value='E.P')

    def test_other_ns_enum_pointer(self):
        self.assert_example(data='A::B::E', usage='A::B::E*', result='A::B::E*', value='A::B::P', arg='&val', imports=('E',), py_value='E.P')

    def test_other_ns_enum_multi_pointer(self):
        self.assert_example(data='A::B::E*', usage='A::B::E**', result='A::B::E**', value='0', arg='&val', py_value='0')

    #----------------------------------------------------------------------
    # Explicitly referenced class in the same namespace
    def test_same_ns_explicit_class(self):
        self.assert_example(data='C::D::Y', usage='C::D::Y', result='C::D::Y', value='C::D::Y()', arg='val', imports=('Y',), py_value='Y()')

    def test_same_ns_explicit_class_ref(self):
        self.assert_example(data='C::D::Y', usage='C::D::Y&', result='C::D::Y', value='C::D::Y()', arg='val', imports=('Y',), py_value='Y()')

    def test_same_ns_explicit_class_pointer(self):
        self.assert_example(data='C::D::Y', usage='C::D::Y*', result='C::D::Y*', value='C::D::Y()', arg='&val', imports=('Y',), py_value='Y()')

    def test_same_ns_explicit_class_multi_pointer(self):
        self.assert_example(data='C::D::Y*', usage='C::D::Y**', result='C::D::Y**', value='0', arg='&val', py_value='0')

    #----------------------------------------------------------------------
    # Implicitly referenced class in the same namespace
    def test_same_ns_implicit_class(self):
        self.assert_example(data='C::D::Y', usage='Y', result='C::D::Y', value='C::D::Y()', arg='val', imports=('Y',), py_value='Y()')

    def test_same_ns_implicit_class_ref(self):
        self.assert_example(data='C::D::Y', usage='Y&', result='C::D::Y', value='C::D::Y()', arg='val', imports=('Y',), py_value='Y()')

    def test_same_ns_implicit_class_pointer(self):
        self.assert_example(data='C::D::Y', usage='Y*', result='C::D::Y*', value='C::D::Y()', arg='&val', imports=('Y',), py_value='Y()')

    def test_same_ns_implicit_class_multi_pointer(self):
        self.assert_example(data='C::D::Y*', usage='Y**', result='C::D::Y**', value='0', arg='&val', py_value='0')

    #----------------------------------------------------------------------
    # Class from a different namespace
    def test_other_ns_class(self):
        self.assert_example(data='A::B::X', usage='A::B::X', result='A::B::X', value='A::B::X()', arg='val', imports=('X',), py_value='X()')

    def test_other_ns_class_ref(self):
        self.assert_example(data='A::B::X', usage='A::B::X&', result='A::B::X', value='A::B::X()', arg='val', imports=('X',), py_value='X()')

    def test_other_ns_class_pointer(self):
        self.assert_example(data='A::B::X', usage='A::B::X*', result='A::B::X*', value='A::B::X()', arg='&val', imports=('X',), py_value='X()')

    def test_other_ns_class_multi_pointer(self):
        self.assert_example(data='A::B::X*', usage='A::B::X**', result='A::B::X**', value='0', arg='&val', py_value='0')

    #----------------------------------------------------------------------
    # Explicitly referenced inner class in the same namespace
    def test_same_ns_explicit_inner_class(self):
        self.assert_example(data='C::D::Y::YInner', usage='C::D::Y::YInner', result='C::D::Y::YInner', value='C::D::Y::YInner()', arg='val', imports=('Y',), py_value='Y.YInner()')

    def test_same_ns_explicit_inner_class_ref(self):
        self.assert_example(data='C::D::Y::YInner', usage='C::D::Y::YInner&', result='C::D::Y::YInner', value='C::D::Y::YInner()', arg='val', imports=('Y',), py_value='Y.YInner()')

    def test_same_ns_explicit_inner_class_pointer(self):
        self.assert_example(data='C::D::Y::YInner', usage='C::D::Y::YInner*', result='C::D::Y::YInner*', value='C::D::Y::YInner()', arg='&val', imports=('Y',), py_value='Y.YInner()')

    def test_same_ns_explicit_inner_class_multi_pointer(self):
        self.assert_example(data='C::D::Y::YInner*', usage='C::D::Y::YInner**', result='C::D::Y::YInner**', value='0', arg='&val', py_value='0')

    #----------------------------------------------------------------------
    # Implicitly referenced inner class in the same namespace
    def test_same_ns_implicit_inner_class(self):
        self.assert_example(data='C::D::Y::YInner', usage='Y::YInner', result='C::D::Y::YInner', value='C::D::Y::YInner()', arg='val', imports=('Y',), py_value='Y.YInner()')

    def test_same_ns_implicit_inner_class_ref(self):
        self.assert_example(data='C::D::Y::YInner', usage='Y::YInner&', result='C::D::Y::YInner', value='C::D::Y::YInner()', arg='val', imports=('Y',), py_value='Y.YInner()')

    def test_same_ns_implicit_inner_class_pointer(self):
        self.assert_example(data='C::D::Y::YInner', usage='Y::YInner*', result='C::D::Y::YInner*', value='C::D::Y::YInner()', arg='&val', imports=('Y',), py_value='Y.YInner()')

    def test_same_ns_implicit_inner_class_multi_pointer(self):
        self.assert_example(data='C::D::Y::YInner*', usage='Y::YInner**', result='C::D::Y::YInner**', value='0', arg='&val', py_value='0')

    #----------------------------------------------------------------------
    # Inner class from a different namespace
    def test_other_ns_inner_class(self):
        self.assert_example(data='A::B::X::XInner', usage='A::B::X::XInner', result='A::B::X::XInner', value='A::B::X::XInner()', arg='val', imports=('X',), py_value='X.XInner()')

    def test_other_ns_inner_class_ref(self):
        self.assert_example(data='A::B::X::XInner', usage='A::B::X::XInner&', result='A::B::X::XInner', value='A::B::X::XInner()', arg='val', imports=('X',), py_value='X.XInner()')

    def test_other_ns_inner_class_pointer(self):
        self.assert_example(data='A::B::X::XInner', usage='A::B::X::XInner*', result='A::B::X::XInner*', value='A::B::X::XInner()', arg='&val', imports=('X',), py_value='X.XInner()')

    def test_other_ns_inner_class_multi_pointer(self):
        self.assert_example(data='A::B::X::XInner*', usage='A::B::X::XInner**', result='A::B::X::XInner**', value='0', arg='&val', py_value='0')


class InlineClassTypeReferencingTestCase(ConverterTestCase, TypeReferencingCases):
    def assert_example(self, **kwargs):
        cpp_source = """
            namespace A {
                namespace B {
                    enum E {
                        P, Q
                    };

                    class X {
                      public:
                        class XInner {};
                    };
                }
            }

            namespace C {
                namespace D {
                    enum F {
                        M, N
                    };

                    class Y {
                      public:
                        class YInner {};
                    };

                    class Z {
                      public:
                        %(usage)s method(%(usage)s value) {
                            return value;
                        }
                    };
                }
            }

            void test() {
                C::D::Z *obj = new C::D::Z();
                %(data)s val = %(value)s;
                %(result)s result = obj->method(%(arg)s);
            }
            """ % kwargs

        # DEBUG: Dump the sample cpp code to a file for external testing.
        # import inspect
        # from .utils import adjust
        # curframe = inspect.currentframe()
        # calframe = inspect.getouterframes(curframe, 2)
        # with open('%s.cpp' % calframe[1][3], 'w') as out:
        #     print(adjust(cpp_source), file=out)

        imports = kwargs.get('imports', tuple())
        imports += ('Z',)
        kwargs['imports'] = ''
        if 'E' in imports or 'X' in imports:
            kwargs['imports'] += 'from test.A.B import %s\n                    ' % ', '.join(
                    imp for imp in sorted(imports)
                    if imp in ('E', 'X')
                )
        if 'F' in imports or 'Y' in imports or 'Z' in imports:
            kwargs['imports'] += 'from test.C.D import %s\n                    ' % ', '.join(
                    imp for imp in sorted(imports)
                    if imp in ('F', 'Y', 'Z')
                )
        if imports:
            kwargs['imports'] += "\n\n                    "

        self.assertMultifileGeneratedOutput(
            cpp=[('test.cpp', cpp_source)],
            py=[
                (
                    'test',
                    """
                    %(imports)sdef test():
                        obj = Z()
                        val = %(py_value)s
                        result = obj.method(val)
                    """ % kwargs
                ),
                (
                    'test.A',
                    """
                    """
                ),
                (
                    'test.A.B',
                    """
                    from enum import Enum


                    class E(Enum):
                        P = 0
                        Q = 1


                    class X:
                        class XInner:
                            pass
                    """
                ),
                (
                    'test.C',
                    """
                    """
                ),
                (
                    'test.C.D',
                    """
                    from enum import Enum


                    class F(Enum):
                        M = 0
                        N = 1


                    class Y:
                        class YInner:
                            pass


                    class Z:
                        def method(self, value):
                            return value
                    """
                ),
            ]
        )


class ClassTypeReferencingTestCase(ConverterTestCase, TypeReferencingCases):
    def assert_example(self, **kwargs):
        cpp_source = """
            namespace A {
                namespace B {
                    enum E {
                        P, Q
                    };

                    class X {
                      public:
                        class XInner {};
                    };
                }
            }

            namespace C {
                namespace D {
                    enum F {
                        M, N
                    };

                    class Y {
                      public:
                        class YInner {};
                    };

                    class Z {
                        %(data)s m_data;
                      public:
                        %(usage)s method(%(usage)s value);
                    };

                    %(usage)s Z::method(%(usage)s value) {
                        return value;
                    }
                }
            }

            void test() {
                C::D::Z *obj = new C::D::Z();
                %(data)s val = %(value)s;
                %(result)s result = obj->method(%(arg)s);
            }
            """ % kwargs

        # DEBUG: Dump the sample cpp code to a file for external testing.
        # import inspect
        # from .utils import adjust
        # curframe = inspect.currentframe()
        # calframe = inspect.getouterframes(curframe, 2)
        # with open('%s.cpp' % calframe[1][3], 'w') as out:
        #     print(adjust(cpp_source), file=out)

        imports = kwargs.get('imports', tuple())
        imports += ('Z',)
        kwargs['imports'] = ''
        if 'E' in imports or 'X' in imports:
            kwargs['imports'] += 'from test.A.B import %s\n                    ' % ', '.join(
                    imp for imp in sorted(imports)
                    if imp in ('E', 'X')
                )
        if 'F' in imports or 'Y' in imports or 'Z' in imports:
            kwargs['imports'] += 'from test.C.D import %s\n                    ' % ', '.join(
                    imp for imp in sorted(imports)
                    if imp in ('F', 'Y', 'Z')
                )
        if imports:
            kwargs['imports'] += "\n\n                    "

        self.assertMultifileGeneratedOutput(
            cpp=[('test.cpp', cpp_source)],
            py=[
                (
                    'test',
                    """
                    %(imports)sdef test():
                        obj = Z()
                        val = %(py_value)s
                        result = obj.method(val)
                    """ % kwargs
                ),
                (
                    'test.A',
                    """
                    """
                ),
                (
                    'test.A.B',
                    """
                    from enum import Enum


                    class E(Enum):
                        P = 0
                        Q = 1


                    class X:
                        class XInner:
                            pass
                    """
                ),
                (
                    'test.C',
                    """
                    """
                ),
                (
                    'test.C.D',
                    """
                    from enum import Enum


                    class F(Enum):
                        M = 0
                        N = 1


                    class Y:
                        class YInner:
                            pass


                    class Z:
                        def method(self, value):
                            return value
                    """
                ),
            ]
        )


class InlineFunctionTypeReferencingTestCase(ConverterTestCase, TypeReferencingCases):
    def assert_example(self, **kwargs):
        cpp_source = """
            namespace A {
                namespace B {
                    enum E {
                        P, Q
                    };

                    class X {
                      public:
                        class XInner {};
                    };
                }
            }

            namespace C {
                namespace D {
                    enum F {
                        M, N
                    };

                    class Y {
                      public:
                        class YInner {};
                    };

                    %(usage)s method(%(usage)s value) {
                        return value;
                    }
                }
            }

            void test() {
                %(data)s val = %(value)s;
                %(result)s result = C::D::method(%(arg)s);
            }
            """ % kwargs

        # DEBUG: Dump the sample cpp code to a file for external testing.
        # import inspect
        # from .utils import adjust
        # curframe = inspect.currentframe()
        # calframe = inspect.getouterframes(curframe, 2)
        # with open('%s.cpp' % calframe[1][3], 'w') as out:
        #     print(adjust(cpp_source), file=out)

        imports = kwargs.get('imports', tuple())
        imports += ('method',)
        kwargs['imports'] = ''
        if 'E' in imports or 'X' in imports:
            kwargs['imports'] += 'from test.A.B import %s\n                    ' % ', '.join(
                    imp for imp in sorted(imports)
                    if imp in ('E', 'X')
                )
        if 'F' in imports or 'method' in imports or 'Y' in imports or 'Z' in imports:
            kwargs['imports'] += 'from test.C.D import %s\n                    ' % ', '.join(
                    imp for imp in sorted(imports)
                    if imp in ('F', 'method', 'Y', 'Z')
                )
        if imports:
            kwargs['imports'] += "\n\n                    "

        self.assertMultifileGeneratedOutput(
            cpp=[('test.cpp', cpp_source)],
            py=[
                (
                    'test',
                    """
                    %(imports)sdef test():
                        val = %(py_value)s
                        result = method(val)
                    """ % kwargs
                ),
                (
                    'test.A',
                    """
                    """
                ),
                (
                    'test.A.B',
                    """
                    from enum import Enum


                    class E(Enum):
                        P = 0
                        Q = 1


                    class X:
                        class XInner:
                            pass
                    """
                ),
                (
                    'test.C',
                    """
                    """
                ),
                (
                    'test.C.D',
                    """
                    from enum import Enum


                    class F(Enum):
                        M = 0
                        N = 1


                    class Y:
                        class YInner:
                            pass


                    def method(value):
                        return value
                    """
                ),
            ]
        )


class FunctionTypeReferencingTestCase(ConverterTestCase, TypeReferencingCases):
    def assert_example(self, **kwargs):
        cpp_source = """
            namespace A {
                namespace B {
                    enum E {
                        P, Q
                    };

                    class X {
                      public:
                        class XInner {};
                    };
                }
            }

            namespace C {
                namespace D {
                    enum F {
                        M, N
                    };

                    class Y {
                      public:
                        class YInner {};
                    };

                    %(usage)s method(%(usage)s value);

                    %(usage)s method(%(usage)s value) {
                        return value;
                    }

                }
            }

            void test() {
                %(data)s val = %(value)s;
                %(result)s result = C::D::method(%(arg)s);
            }
            """ % kwargs

        # DEBUG: Dump the sample cpp code to a file for external testing.
        # import inspect
        # from .utils import adjust
        # curframe = inspect.currentframe()
        # calframe = inspect.getouterframes(curframe, 2)
        # with open('%s.cpp' % calframe[1][3], 'w') as out:
        #     print(adjust(cpp_source), file=out)

        imports = kwargs.get('imports', tuple())
        imports += ('method',)
        kwargs['imports'] = ''
        if 'E' in imports or 'X' in imports:
            kwargs['imports'] += 'from test.A.B import %s\n                    ' % ', '.join(
                    imp for imp in sorted(imports)
                    if imp in ('E', 'X')
                )
        if 'F' in imports or 'method' in imports or 'Y' in imports or 'Z' in imports:
            kwargs['imports'] += 'from test.C.D import %s\n                    ' % ', '.join(
                    imp for imp in sorted(imports)
                    if imp in ('F', 'method', 'Y', 'Z')
                )
        if imports:
            kwargs['imports'] += "\n\n                    "

        self.assertMultifileGeneratedOutput(
            cpp=[('test.cpp', cpp_source)],
            py=[
                (
                    'test',
                    """
                    %(imports)sdef test():
                        val = %(py_value)s
                        result = method(val)
                    """ % kwargs
                ),
                (
                    'test.A',
                    """
                    """
                ),
                (
                    'test.A.B',
                    """
                    from enum import Enum


                    class E(Enum):
                        P = 0
                        Q = 1


                    class X:
                        class XInner:
                            pass
                    """
                ),
                (
                    'test.C',
                    """
                    """
                ),
                (
                    'test.C.D',
                    """
                    from enum import Enum


                    class F(Enum):
                        M = 0
                        N = 1


                    class Y:
                        class YInner:
                            pass


                    def method(value):
                        return value
                    """
                ),
            ]
        )
