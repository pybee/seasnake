###########################################################################
# Data model
#
# This is a transitional AST structure; it defines an object model that
# is structured like C++, but outputs Python. At the top of the tree is
# a Module definition.
###########################################################################
from __future__ import unicode_literals, print_function

import sys

from collections import OrderedDict

from clang.cindex import TypeKind

# Python 2 compatibility shims
if sys.version_info.major <= 2:
    text = unicode
else:
    text = str


__all__ = (
    'CONSUMED', 'UNDEFINED',
    'Module',
    'Enumeration', 'EnumValue',
    'Function', 'Parameter', 'Variable',
    'Typedef',
    'Class', 'Struct', 'Union',
    'Attribute', 'Constructor', 'Destructor', 'Method',
    'Return', 'Block', 'If', 'Do', 'While', 'For',
    'Break', 'Continue',
    'VariableReference', 'TypeReference', 'PrimitiveTypeReference', 'AttributeReference', 'SelfReference',
    'Literal', 'ListLiteral',
    'UnaryOperation', 'BinaryOperation', 'ConditionalOperation',
    'Parentheses', 'ArraySubscript',
    'Cast', 'Invoke', 'New',
)


# A marker for token use during macro expansion
CONSUMED = object()

# A marker for unknown values
UNDEFINED = object()


class Expression(object):
    # An expression is the left node of the AST. Operations,
    # literals, and references to attributes/members are all
    # expresisons. Expressions don't have context
    def __repr__(self):
        return "<%s>" % (self.__class__.__name__)

    def clean_argument(self):
        return self


class Declaration(Expression):
    # A Declaration is a named expression. As they are named,
    # They must belong to a context; that context provides the
    # scope in which the declaration is valid.
    # An anonymous declaration is a declaration without a
    # discoverable name.
    def __init__(self, context, name):
        self._name = None

        self.context = context
        self.name = name

    def __repr__(self):
        try:
            return "<%s %s>" % (self.__class__.__name__, self.full_name)
        except:
            return "<%s %s>" % (self.__class__.__name__, self.name)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        # If there has been a change of name (usually due to an anonymous
        # declaration being typedef'd) make sure the name dictionary is
        # updated to reflect the new name.
        if self.context and self._name:
            del self.context.names[self._name]

        self._name = value

        if self.context and value:
            self.context.names[value] = self

    @property
    def full_name(self):
        if self.context:
            return '::'.join([self.context.full_name, self.name])
        return self.name

    @property
    def root(self):
        if self.context is None:
            return self
        else:
            return self.context.root


class Context(Declaration):
    # A context is a scope in for declaration names. Contexts
    # are heirarchical - the can be part of other contexts.
    # There can also be related contexts; these are alternate
    # sources of names.
    def __init__(self, context, name):
        super(Context, self).__init__(context=context, name=name)
        self.names = OrderedDict()
        self.related_contexts = set()

    def __getitem__(self, name):
        return self.__getitem(name, set())

    def __getitem(self, name, looked):
        if self in looked:
            raise KeyError(name)

        looked.add(self)

        # The name we're looking for might be annotated with
        # const, class, or any number of other descriptors.
        # Remove them, and then remove any extra spaces so that
        # we're left with a compact type name.
        name = name.replace('const', '')
        name = name.replace('class', '')
        name = name.replace('virtual', '')
        name = name.replace(' ', '')

        # If the name is scoped, do a lookup from the root node.
        # Otherwise, just look up the name in the current context.
        if '::' in name:
            parts = name.split('::')
            # print("LOOK FOR NAME", parts)
            decl = self.root
            for part in parts:
                decl = decl[part]
            return decl
        else:
            try:
                # print("LOOK FOR NAME PART", name, "in", self.name, '->', self.names)
                return self.names[name]
            except KeyError:
                if self.context:
                    try:
                        return self.context.__getitem(name, looked)
                    except KeyError:
                        pass

                for related in self.related_contexts:
                    # print("LOOK FOR NAME PART IN RELATED NAMESPACE", related)
                    try:
                        return related.__getitem(name, looked)
                    except KeyError:
                        pass

                raise


###########################################################################
# Modules
###########################################################################

class Module(Context):
    def __init__(self, name, context=None):
        super(Module, self).__init__(context=context, name=name)
        self.declarations = []
        self.classes = set()

        self.imports = {}
        self.submodules = {}
        self.module = self
        self.using = None

    @property
    def is_module(self):
        return True

    def add_to_context(self, context):
        context.add_submodule(self)

    def add_class(self, klass):
        if klass not in self.classes:
            self.declarations.append(klass)
            self.classes.add(klass)
        klass.add_imports(self)

    def add_struct(self, struct):
        if struct not in self.classes:
            self.declarations.append(struct)
            self.classes.add(struct)
        struct.add_imports(self)

    def add_union(self, union):
        if union not in self.classes:
            self.declarations.append(union)
            self.classes.add(union)
        union.add_imports(self)

    def add_function(self, function):
        self.declarations.append(function)
        function.add_imports(self)

    def add_enumeration(self, enum):
        self.declarations.append(enum)
        enum.add_imports(self)

    def add_class_attribute(self, attr):
        # Class attributes might be added to this context because of
        # the way they're declared, but they actually belong to
        # the context in which they're declared (which should be
        # a child of *this* module).
        attr.context.add_class_attribute(attr)
        attr.add_imports(self)

    def add_attribute(self, attr):
        # Attributes might be added to this context because of
        # the way they're declared, but they actually belong to
        # the context in which they're declared (which should be
        # a child of *this* module).
        attr.context.add_attribute(attr)
        attr.add_imports(self)

    def add_variable(self, var):
        self.declarations.append(var)
        var.add_imports(self)

    def add_statement(self, statement):
        self.declarations.append(statement)
        statement.add_imports(self)

    def add_import(self, path, symbol=None):
        self.imports.setdefault(path, set()).add(symbol)

    def add_imports(self, context):
        pass

    def add_submodule(self, module):
        self.submodules[module.name] = module
        
    def add_using_decl(self, decl):
        if not self.using:
            self.using = Context(None, 'using-placeholder')
            self.related_contexts.add(self.using)
            
        self.using.names[decl.name] = decl

    def output(self, out):
        if self.imports:
            for path in sorted(self.imports):
                if self.imports[path]:
                    out.write('from %s import %s' % (
                        path,
                        ', '.join(sorted(self.imports[path]))
                    ))
                else:
                    out.write('import %s' % path)
                out.clear_line()

        out.clear_major_block()
        for decl in self.declarations:
            # Ignore symbols that are known to be internal.
            if self.context is None and decl.name in (
                        'ptrdiff_t', 'max_align_t', 'va_list', '__gnuc_va_list'
                    ):
                continue
            out.clear_minor_block()
            decl.output(out)
        out.clear_line()


###########################################################################
# Parent
###########################################################################

class Parent(Context):
    # Parent is a base class for all contexts that aren't modules.
    def __init__(self, context, name):
        super(Parent, self).__init__(context=context, name=name)
        self.names = OrderedDict()

    @property
    def module(self):
        "Return the name of the module that contains the declaration of this type"
        context = self.context
        while not context.is_module:
            context = context.context
        return context

    @property
    def module_name(self):
        """Return the fully qualified name of this type within the module.

        For example, given:

        class Foo:
            class Bar:
                pass


        class Foo has a module name of "Foo"
        class Bar has a module name of "Foo.Bar"
        """
        if not self.name:
            return

        mod_name_parts = [self.name]
        context = self.context
        while not context.is_module:
            mod_name_parts.append(context.name)
            context = context.context

        # The module name is the name required to get to a declaration
        # inside a module.
        mod_name_parts.reverse()
        return '.'.join(mod_name_parts)

    @property
    def import_name(self):
        """Return the name that must be imported to get access to this node.

        For example, given:

        class Foo:
            class Bar:
                pass

        the import name for both Foo and Bar is "Foo".
        """
        if not self.name:
            return

        context = self
        while not context.context.is_module:
            context = context.context

        return context.name

    @property
    def is_module(self):
        return False


###########################################################################
# Enumerated types
###########################################################################

class Enumeration(Parent):
    def __init__(self, context, name):
        super(Enumeration, self).__init__(context=context, name=name)
        self.enumerators = []

    def add_enumerator(self, enumerator):
        self.enumerators.append(enumerator)
        self.context.names[enumerator.name] = enumerator
        enumerator.enumeration = self

    def add_to_context(self, context):
        context.add_enumeration(self)

    def add_imports(self, context):
        context.module.add_import('enum', 'Enum')

    def output(self, out):
        out.clear_major_block()
        out.write("class %s(Enum):" % self.name)
        out.start_block()
        if self.enumerators:
            for enumerator in self.enumerators:
                out.clear_line()
                out.write("%s = %s" % (
                    enumerator.name, enumerator.value
                ))
        else:
            out.clear_line()
            out.write('pass')
        out.end_block()
        out.clear_major_block()


class EnumValue(Declaration):
    # A value in an enumeration.
    # EnumValues are slightly odd, becaues they are Declarations
    # in the same context as the Enumeration they belong to.
    def __init__(self, context, name, value):
        super(EnumValue, self).__init__(context, name)
        self.name = name
        self.value = value
        self.enumeration = None

    def add_imports(self, context):
        if context.module != self.context.module:
            context.module.add_import(
                self.context.module.full_name.replace('::', '.'),
                self.context.name
            )

    def output(self, out):
        out.write('%s.%s' % (self.enumeration.module_name, self.name))


###########################################################################
# Functions
###########################################################################

class Function(Parent):
    def __init__(self, context, name):
        super(Function, self).__init__(context=context, name=name)
        self.parameters = []
        self.statements = None

    def add_parameter(self, parameter):
        self.parameters.append(parameter)

    def add_to_context(self, context):
        context.add_function(self)

    def add_import(self, scope, name):
        self.context.add_import(scope, name)

    def add_imports(self, context):
        for param in self.parameters:
            param.add_imports(context)

    def add_statement(self, statement):
        self.statements.append(statement)
        statement.add_imports(self)

    def output(self, out):
        out.clear_major_block()
        out.write('def %s(' % self.name)
        for i, param in enumerate(self.parameters):
            if i != 0:
                out.write(', ')
            param.output(out)
        out.write('):')
        out.start_block()
        if self.statements:
            for statement in self.statements:
                out.clear_line()
                statement.output(out)
        else:
            out.clear_line()
            out.write('pass')
        out.end_block()
        out.clear_major_block()


class Parameter(Declaration):
    def __init__(self, function, name, ctype, default):
        super(Parameter, self).__init__(context=function, name=name)
        self.ctype = ctype
        self.default = default

    @property
    def module_name(self):
        return self.name

    def add_to_context(self, context):
        context.add_parameter(self)

    def add_imports(self, context):
        if self.default is not UNDEFINED and self.default is not None:
            self.default.add_imports(context)

    def output(self, out):
        out.write(self.name)
        if self.default is None:
            out.write('=None')
        elif self.default is not UNDEFINED:
            out.write('=')
            self.default.output(out)


class Variable(Declaration):
    def __init__(self, context, name, value):
        super(Variable, self).__init__(context=context, name=name)
        self.value = value

    @property
    def module_name(self):
        return self.name

    def add_to_context(self, context):
        context.add_variable(self)

    def add_imports(self, context):
        if self.value and self.value is not UNDEFINED:
            self.value.add_imports(context)

    def output(self, out):
        if self.value is not UNDEFINED:
            out.write('%s = ' % self.name.replace('::', '.'))
            if self.value:
                self.value.output(out)
            else:
                out.write('None')
            out.clear_line()


class Typedef(Declaration):
    def __init__(self, context, name, typ):
        super(Typedef, self).__init__(context=context, name=name)
        self.type = typ

    @property
    def module(self):
        return self.context.module

    @property
    def module_name(self):
        return self.name

    def add_to_context(self, context):
        context.add_variable(self)

    def add_imports(self, context):
        self.type.add_imports(context)

    def output(self, out):
        out.write('%s = ' % self.name)
        self.type.output(out)
        out.clear_line()


###########################################################################
# Structs
###########################################################################

class Struct(Parent):
    def __init__(self, context, name):
        super(Struct, self).__init__(context=context, name=name)
        self._superclass = None
        self.constructors = {}
        self.destructor = None
        self.class_attributes = OrderedDict()
        self.attributes = OrderedDict()
        self.methods = OrderedDict()
        self.classes = OrderedDict()

    @property
    def superclass(self):
        return self._superclass

    @superclass.setter
    def superclass(self, ref):
        ref.add_imports(self)
        self._superclass = ref.type
        self.related_contexts.add(ref.type)

    def add_imports(self, context):
        for constructor in self.constructors.values():
            constructor.add_imports(context)

        for attr in self.class_attributes.values():
            attr.add_imports(context)

        for attr in self.attributes.values():
            attr.add_imports(context)

        for klass in self.classes.values():
            klass.add_imports(context)

        for method in self.methods.values():
            method.add_imports(context)

    def add_class(self, klass):
        self.classes[klass.name] = klass

    def add_struct(self, struct):
        self.classes[struct.name] = struct

    def add_union(self, union):
        self.classes[union.name] = union

    def add_constructor(self, method):
        print("Ignoring constructor for struct %s" % self.name, file=sys.stderr)

    def add_destructor(self, method):
        if self.destructor:
            if self.destructor.statements is None:
                self.destructor = method
            else:
                raise Exception("Cannot handle multiple desructors")
        else:
            self.destructor = method

    def add_class_attribute(self, attr):
        self.class_attributes[attr.name] = attr

    def add_attribute(self, attr):
        self.attributes[attr.name] = attr

    def add_method(self, method):
        self.methods[method.name] = method

    def add_variable(self, var):
        self.class_attributes[var.name] = var

    def add_to_context(self, context):
        context.add_struct(self)

    def output(self, out):
        out.clear_major_block()
        if self.superclass:
            out.write("class %s(%s):" % (self.name, self.superclass.module_name))
        else:
            out.write("class %s:" % self.name)
        out.start_block()

        if self.class_attributes or self.attributes or self.destructor or self.classes or self.methods:
            if self.class_attributes:
                for name, variable in self.class_attributes.items():
                    out.clear_line()
                    variable.output(out)
                out.clear_minor_block()

            if self.attributes:
                out.clear_line()
                params = ''.join(', %s=None' % name for name in self.attributes.keys())
                out.write('def __init__(self%s):' % params)
                out.start_block()
                for name, attr in self.attributes.items():
                    out.clear_line()
                    attr.output(out, init=True)
                out.end_block()

            if self.destructor:
                self.destructor.output(out)

            for name, klass in self.classes.items():
                klass.output(out)

            for name, method in self.methods.items():
                method.output(out)
        else:
            out.clear_line()
            out.write('pass')
        out.end_block()
        out.clear_major_block()


###########################################################################
# Unions
###########################################################################

class Union(Parent):
    def __init__(self, context, name):
        super(Union, self).__init__(context=context, name=name)
        self._superclass = None
        self.class_attributes = OrderedDict()
        self.attributes = OrderedDict()
        self.enumerations = OrderedDict()
        self.methods = OrderedDict()
        self.classes = OrderedDict()

    @property
    def superclass(self):
        return self._superclass

    @superclass.setter
    def superclass(self, ref):
        ref.add_imports(self)
        self._superclass = ref.type
        self.related_contexts.add(ref.type)

    def add_imports(self, context):
        for attr in self.class_attributes.values():
            attr.add_imports(context)

        for attr in self.attributes.values():
            attr.add_imports(context)

        for klass in self.classes.values():
            klass.add_imports(context)

        for method in self.methods.values():
            method.add_imports(context)

    def add_class(self, klass):
        self.classes[klass.name] = klass

    def add_struct(self, struct):
        self.classes[struct.name] = struct

    def add_union(self, union):
        self.classes[union.name] = union

    def add_class_attribute(self, var):
        self.class_attributes[var.name] = var

    def add_attribute(self, attr):
        self.attributes[attr.name] = attr

    def add_enumeration(self, enum):
        self.enumerations[enum.name] = enum

    def add_method(self, method):
        self.methods[method.name] = method

    def add_to_context(self, context):
        context.add_union(self)

    def output(self, out):
        out.clear_major_block()
        out.write("class %s:" % self.name)
        out.start_block()
        if self.class_attributes or self.attributes or self.classes or self.methods:
            if self.class_attributes:
                for name, variable in self.class_attributes.items():
                    out.clear_line()
                    variable.output(out)
                out.clear_minor_block()

            if self.attributes:
                params = ''.join(', %s=None' % name for name in self.attributes.keys())
                out.clear_line()
                out.write('def __init__(self%s):' % params)
                out.start_block()
                for name, attr in self.attributes.items():
                    out.clear_line()
                    attr.output(out, init=True)
                out.end_block()

            for name, enum in self.enumerations.items():
                enum.output(out)

            for name, klass in self.classes.items():
                klass.output(out)

            for name, method in self.methods.items():
                method.output(out)
        else:
            out.clear_line()
            out.write('pass')

            out.end_block()
        out.end_block()
        out.clear_major_block()


###########################################################################
# Classes
###########################################################################

class Class(Parent):
    def __init__(self, context, name):
        super(Class, self).__init__(context=context, name=name)
        self._superclass = None
        self.constructors = {}
        self.destructor = None
        self.class_attributes = OrderedDict()
        self.attributes = OrderedDict()
        self.enumerations = OrderedDict()
        self.methods = OrderedDict()
        self.classes = OrderedDict()

    @property
    def superclass(self):
        return self._superclass

    @superclass.setter
    def superclass(self, ref):
        ref.add_imports(self)
        self._superclass = ref.type
        self.related_contexts.add(ref.type)

    def add_imports(self, context):
        for constructor in self.constructors.values():
            constructor.add_imports(context)

        for attr in self.class_attributes.values():
            attr.add_imports(context)

        for attr in self.attributes.values():
            attr.add_imports(context)

        for enum in self.enumerations.values():
            enum.add_imports(context)

        for klass in self.classes.values():
            klass.add_imports(context)

        for method in self.methods.values():
            method.add_imports(context)

    def add_class(self, klass):
        self.classes[klass.name] = klass

    def add_struct(self, struct):
        self.classes[struct.name] = struct

    def add_union(self, union):
        self.classes[union.name] = union

    def add_constructor(self, method):
        signature = tuple(p.ctype for p in method.parameters)
        self.constructors[signature] = method

        if len(self.constructors) > 1:
            print("Multiple constructors for class %s (adding [%s])" % (
                    self.name,
                    ','.join(s for s in signature),
                ),
                file=sys.stderr
            )

    def add_destructor(self, method):
        if self.destructor:
            if self.destructor.statements is None:
                self.destructor = method
            else:
                raise Exception("Cannot handle multiple desructors")
        else:
            self.destructor = method

    def add_class_attribute(self, var):
        self.class_attributes[var.name] = var

    def add_attribute(self, attr):
        self.attributes[attr.name] = attr

    def add_method(self, method):
        self.methods[method.name] = method

    def add_enumeration(self, enum):
        self.enumerations[enum.name] = enum

    def add_variable(self, var):
        self.class_attributes[var.name] = var

    def add_to_context(self, context):
        context.add_class(self)

    def output(self, out):
        out.clear_major_block()
        if self.superclass:
            out.write("class %s(%s):" % (self.name, self.superclass.module_name))
        else:
            out.write("class %s:" % self.name)
        out.start_block()
        if self.class_attributes or self.attributes or self.constructors or self.destructor or self.enumerations or self.classes or self.methods:
            if self.class_attributes:
                for name, variable in self.class_attributes.items():
                    out.clear_line()
                    variable.output(out)
                out.clear_minor_block()

            for signature, constructor in sorted(self.constructors.items()):
                constructor.output(out)

            if self.destructor:
                self.destructor.output(out)

            for name, enum in self.enumerations.items():
                enum.output(out)

            for name, klass in self.classes.items():
                klass.output(out)

            for name, method in self.methods.items():
                method.output(out)
        else:
            out.clear_line()
            out.write('pass')
        out.end_block()
        out.clear_major_block()


###########################################################################
# Class/Struct/Union components
###########################################################################

class Attribute(Declaration):
    def __init__(self, klass, name, value=None, static=False):
        super(Attribute, self).__init__(context=klass, name=name)
        self.value = value
        self.static = static

    @property
    def module(self):
        return self.context.module

    @property
    def module_name(self):
        return self.context.name + '.' + self.name

    def add_to_context(self, context):
        if self.static:
            context.add_class_attribute(self)
        else:
            context.add_attribute(self)

    def add_imports(self, context):
        if self.value:
            self.value.add_imports(context)

    def output(self, out, init=False):
        if not self.static:
            out.write('self.')
        out.write('%s = ' % self.name)
        if init:
            if self.value:
                out.write('%s if %s else ' % (self.name, self.name))
                self.value.output(out)
            else:
                out.write(self.name)
        else:
            if self.value:
                self.value.output(out)
            else:
                out.write('None')
        out.clear_line()


class Constructor(Parent):
    def __init__(self, klass):
        super(Constructor, self).__init__(context=klass, name=None)
        self.parameters = []
        self.statements = []

    def __repr__(self):
        return '<Constructor %s>' % self.context.full_name

    def add_parameter(self, parameter):
        self.parameters.append(parameter)

    def add_to_context(self, klass):
        self.context.add_constructor(self)

    def add_attribute(self, attr):
        self.context.add_attribute(attr)

    def add_imports(self, context):
        for param in self.parameters:
            param.add_imports(context)

    def add_statement(self, statement):
        self.statements.append(statement)
        statement.add_imports(self.context)

    def output(self, out):
        out.clear_minor_block()
        out.write("def __init__(self")
        if self.parameters:
            for param in self.parameters:
                out.write(', ')
                param.output(out)
        out.write('):')
        out.start_block()
        if self.context.attributes or self.statements:
            has_init = False
            for name, attr in self.context.attributes.items():
                if attr.value is not None:
                    out.clear_line()
                    attr.output(out)
                    has_init = True

            if self.statements:
                for statement in self.statements:
                    out.clear_line()
                    statement.output(out)
            elif not has_init:
                out.clear_line()
                out.write('pass')

        else:
            out.clear_line()
            out.write('pass')
        out.end_block()


class Destructor(Parent):
    def __init__(self, klass):
        super(Destructor, self).__init__(context=klass, name=None)
        self.parameters = []
        self.statements = None

    def add_to_context(self, klass):
        self.context.add_destructor(self)

    def add_imports(self, context):
        pass

    def add_statement(self, statement):
        if self.statements:
            self.statements.append(statement)
        else:
            self.statements = [statement]
        statement.add_imports(self.context)

    def output(self, out):
        out.clear_minor_block()
        out.write("def __del__(self):")
        out.start_block()
        if self.statements:
            for statement in self.statements:
                out.clear_line()
                statement.output(out)
        else:
            out.clear_line()
            out.write('pass')
        out.end_block()


class Method(Parent):
    def __init__(self, klass, name, pure_virtual, static):
        super(Method, self).__init__(context=klass, name=name)
        self.parameters = []
        self.statements = None
        self.pure_virtual = pure_virtual
        self.static = static

    def add_parameter(self, parameter):
        self.parameters.append(parameter)

    def add_to_context(self, context):
        self.context.add_method(self)

    def add_imports(self, context):
        for param in self.parameters:
            param.add_imports(context)

        if self.statements:
            for statement in self.statements:
                statement.add_imports(context)

    def add_statement(self, statement):
        if self.statements:
            self.statements.append(statement)
        else:
            self.statements = [statement]
        statement.add_imports(self.context)

    def output(self, out):
        out.clear_minor_block()
        if self.static:
            out.write("@staticmethod")
            out.clear_line()
            out.write('def %s(' % self.name)
        else:
            out.write('def %s(self' % self.name)

        for i, param in enumerate(self.parameters):
            if i != 0 or not self.static:
                out.write(', ')
            param.output(out)
        out.write('):')

        out.start_block()
        if self.statements:
            for statement in self.statements:
                out.clear_line()
                statement.output(out)
        elif self.pure_virtual:
            out.clear_line()
            out.write('raise NotImplementedError()')
        else:
            out.clear_line()
            out.write('pass')
        out.end_block()


###########################################################################
# Statements
###########################################################################

class Block(Parent):
    def __init__(self, context):
        super(Block, self).__init__(context=context, name=None)
        self.statements = []

    def __repr__(self):
        return '<Block>'

    def add_statement(self, statement):
        self.statements.append(statement)

    def add_imports(self, context):
        for statement in self.statements:
            statement.add_imports(context)

    def output(self, out):
        out.start_block()
        if self.statements:
            for statement in self.statements:
                out.clear_line()
                statement.output(out)
        else:
            out.clear_line()
            out.write('pass')
        out.end_block()


class Return(Expression):
    def __init__(self):
        self.value = None

    def add_imports(self, context):
        if self.value:
            self.value.add_imports(context)

    def add_expression(self, expr):
        self.value = expr

    def output(self, out):
        out.write('return')
        if self.value:
            out.write(' ')
            self.value.output(out)
        out.clear_line()


class If(Parent):
    def __init__(self, condition, context):
        super(If, self).__init__(context, name=None)
        self.condition = condition
        self.if_true = Block(self)
        self.if_false = None

    def __repr__(self):
        return '<If %s>' % self.condition

    def add_imports(self, context):
        self.condition.add_imports(context)
        self.if_true.add_imports(context)
        if self.if_false:
            self.if_false.add_imports(context)

    def output(self, out, is_elif=False):
        out.clear_line()
        out.write('elif ' if is_elif else 'if ')
        self.condition.output(out)
        out.write(':')

        self.if_true.output(out)

        if self.if_false is not None:
            if isinstance(self.if_false, If):
                self.if_false.output(out, is_elif=True)
            else:
                out.clear_line()
                out.write('else:')
                if isinstance(self.if_false, Block):
                    self.if_false.output(out)
                else:
                    out.clear_line()
                    out.start_block()
                    self.if_false.output(out)
                    out.end_block()


class Do(Parent):
    def __init__(self, context):
        super(Do, self).__init__(context, name=None)
        self.condition = None
        self.statements = Block(self)
        
    def __repr__(self):
        return '<Do %s>' % self.condition
    
    def add_imports(self, context):
        self.condition.add_imports(context)
        self.statements.add_imports(context)
    
    def output(self, out):
        out.clear_line()
        out.write('while True:')
        
        if self.statements.statements:
            self.statements.output(out)
        
        out.clear_line()
        out.start_block()
        out.write('if not (') # invert the condition
        self.condition.output(out)
        out.write('):')
        
        out.start_block()
        out.clear_line()
        out.write('break')
        out.end_block()
        out.end_block()
        
        out.end_block()

class While(Parent):
    def __init__(self, condition, context):
        super(While, self).__init__(context, name=None)
        self.condition = condition
        self.statements = Block(self)
        
    def __repr__(self):
        return '<While %s>' % self.condition
    
    def add_imports(self, context):
        self.condition.add_imports(context)
        self.statements.add_imports(context)
    
    def output(self, out):
        out.clear_line()
        out.write('while ')
        self.condition.output(out)
        out.write(':')
        
        self.statements.output(out)


class For(Parent):
    def __init__(self, init_stmt, expr_stmt, end_expr, context):
        super(For, self).__init__(context, name=None)
        self.init_stmt = init_stmt
        self.expr_stmt = expr_stmt
        self.end_expr = end_expr
        self.statements = Block(self)
        
    def __repr__(self):
        return '<For %s>' % self.condition
    
    def add_imports(self, context):
        if self.init_stmt:
            self.init_stmt.add_imports(context)
        if self.expr_stmt:
            self.expr_stmt.add_imports(context)
        if self.end_expr:
            self.end_expr.add_imports(context)
        
        self.statements.add_imports(context)
    
    def output(self, out):
        out.clear_line()
        # TODO: convert simple expressions to a range statement
        
        if self.init_stmt:
            self.init_stmt.output(out)
        
        if self.expr_stmt:
            out.write('while ')
            self.expr_stmt.output(out)
            out.write(':')
        else:
            out.write('while True:')
        
        # suppress the extra pass
        if self.statements.statements or not self.end_expr:
            self.statements.output(out)
        
        if self.end_expr:
            out.start_block()
            out.clear_line()
            self.end_expr.output(out)
            out.end_block()
        
class Break(object):
    
    def add_imports(self, context):
        pass
    
    def output(self, out):
        out.clear_line()
        out.write('break')
        out.clear_line()


class Continue(object):
    
    def __init__(self, end_expr):
        self.end_expr = end_expr
    
    def add_imports(self, context):
        pass
    
    def output(self, out):
        out.clear_line()
        # this exists for when a continue is used inside of a for
        # loop that has an incrementing expression in it
        if self.end_expr:
            self.end_expr.output(out)
            out.clear_line()
        out.write('continue')
        out.clear_line()

###########################################################################
# References to variables and types
###########################################################################

# A reference to a variable
class VariableReference(Expression):
    def __init__(self, var, node):
        self.var = var
        self.node = node

    @property
    def name(self):
        return self.var.name

    @property
    def module(self):
        return self.var.context.module

    @property
    def module_name(self):
        return self.var.module_name

    @property
    def import_name(self):
        return self.var.module_name

    def add_imports(self, context):
        # If the type being referenced isn't from the same module
        # then an import will be required.
        if context.module != self.module:
            context.module.add_import(
                self.module.full_name.replace('::', '.'),
                self.import_name
            )

    def output(self, out):
        out.write(self.module_name)


# A reference to a type
class TypeReference(Expression):
    def __init__(self, typ):
        self.type = typ

    @property
    def name(self):
        return self.type.name

    @property
    def module(self):
        return self.type.context.module

    @property
    def module_name(self):
        return self.type.module_name

    @property
    def import_name(self):
        return self.type.import_name

    def __repr__(self):
        return '<TypeReference %s>' % self.type

    def add_imports(self, context):
        # If the type being referenced isn't from the same module
        # then an import will be required.
        if context.module != self.type.module:
            context.module.add_import(
                self.type.module.full_name.replace('::', '.'),
                self.import_name
            )

    def output(self, out):
        out.write(self.module_name)


# A reference to a primitive type
class PrimitiveTypeReference(Expression):
    def __init__(self, name):
        self.name = name

    def add_imports(self, context):
        pass

    def output(self, out):
        out.write(self.name)


# A reference to self.
class SelfReference(Expression):
    def add_imports(self, context):
        pass

    def output(self, out):
        out.write('self')


# A reference to an attribute on a class
class AttributeReference(Expression):
    def __init__(self, instance, attr):
        self.instance = instance
        self.name = attr

    # def add_to_context(self, context):
    #     pass

    def add_imports(self, context):
        self.instance.add_imports(context)

    def output(self, out):
        self.instance.output(out)
        out.write('.%s' % self.name)


###########################################################################
# Literals
###########################################################################

class Literal(Expression):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.value)

    def add_imports(self, context):
        pass

    def output(self, out):
        out.write(text(self.value))


class ListLiteral(Expression):
    def __init__(self):
        self.value = []

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.value)

    def add_imports(self, context):
        for value in self.value:
            value.add_imports(context)

    def append(self, item):
        self.value.append(item)

    def output(self, out):
        out.write('[')
        for i, item in enumerate(self.value):
            if i != 0:
                out.write(', ')
            item.output(out)
        out.write(']')


###########################################################################
# Expressions
###########################################################################

class UnaryOperation(Expression):
    def __init__(self, op, value):
        self.name = op
        self.value = value

    def add_imports(self, context):
        self.value.add_imports(context)

    def output(self, out, depth=0):
        out.write('    ' * depth)
        python_op = {
            '!': 'not ',
            '~': '~',
        }.get(self.name, self.name)

        # while this will often end up with incorrect python,
        # better than silently failing on ++/-- (which don't do
        # anything in python)
        if python_op == '++':
            self.value.output(out)
            out.write(' += 1')
        elif python_op == '--':
            out.write(python_op)
            out.write(' -= 1')
        else:
            out.write(python_op)
            self.value.output(out)

    def clean_argument(self):
        # Strip dereferencing operators
        if self.name == '&':
            return self.value.clean_argument()
        elif self.name == '*':
            return self.value.clean_argument()
        else:
            return self


class BinaryOperation(Expression):
    def __init__(self, lvalue, op, rvalue):
        self.lvalue = lvalue
        self.name = op
        self.rvalue = rvalue

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.name)

    def add_imports(self, context):
        self.lvalue.add_imports(context)
        self.rvalue.add_imports(context)

    def add_to_context(self, context):
        context.add_statement(self)

    def output(self, out, depth=0):
        self.lvalue.output(out)
        python_op = {
            # Equality
            '=': ' = ',

            # Arithmetic
            '+': ' + ',
            '-': ' - ',
            '*': ' * ',
            '/': ' / ',
            '%': ' % ',

            # Comparison
            '==': ' == ',
            '!=': ' != ',
            '>': ' > ',
            '<': ' < ',
            '>=': ' >= ',
            '<=': ' <= ',

            # Bitwise
            '&': ' & ',
            '|': ' | ',
            '^': ' ^ ',
            '<<': ' << ',
            '>>': ' >> ',

            # Assignment
            '+=': ' += ',
            '-=': ' -= ',
            '*=': ' *= ',
            '/=': ' /= ',
            '%=': ' %= ',

            '&=': ' &= ',
            '|=': ' |= ',
            '^=': ' ^= ',
            '<<=': ' <<= ',
            '>>=': ' >>= ',

            # Logical
            '&&': ' and ',
            '||': ' or ',

        }.get(self.name, self.name)

        out.write(python_op)
        self.rvalue.output(out)


class ConditionalOperation(Expression):
    def __init__(self, condition, true_result, false_result):
        self.condition = condition
        self.true_result = true_result
        self.false_result = false_result

    def add_imports(self, context):
        self.condition.add_imports(context)
        self.true_result.add_imports(context)
        self.false_result.add_imports(context)

    def output(self, out):
        self.true_result.output(out)
        out.write(' if ')
        self.condition.output(out)
        out.write(' else ')
        self.false_result.output(out)


class Parentheses(Expression):
    def __init__(self, body):
        self.body = body

    def add_imports(self, context):
        self.body.add_imports(context)

    def output(self, out):
        if isinstance(self.body, (BinaryOperation, ConditionalOperation)):
            out.write('(')
            self.body.output(out)
            out.write(')')
        else:
            self.body.output(out)


class ArraySubscript(Expression):
    def __init__(self, value, index):
        self.value = value
        self.index = index

    def add_imports(self, context):
        self.value.add_imports(context)
        self.index.add_imports(context)

    def output(self, out):
        self.value.output(out)
        out.write('[')
        self.index.output(out)
        out.write(']')

    def clean_argument(self):
        return self


class Cast(Expression):
    def __init__(self, typekind, value):
        self.typekind = typekind
        self.value = value

    def __repr__(self):
        return "<Cast %s>" % self.typekind

    def add_imports(self, context):
        self.value.add_imports(context)

    def output(self, out):
        # Primitive types are cast using Python casting.
        # Other types are passed through as ducks.
        if self.typekind == TypeKind.BOOL:
            out.write('bool(')
            self.value.output(out)
            out.write(')')
        elif self.typekind in (
                    TypeKind.CHAR_U,
                    TypeKind.UCHAR,
                    TypeKind.CHAR16,
                    TypeKind.CHAR32,
                    TypeKind.CHAR_S,
                    TypeKind.SCHAR,
                    TypeKind.WCHAR,
                ):
            out.write('str(')
            self.value.output(out)
            out.write(')')
        elif self.typekind in (
                    TypeKind.USHORT,
                    TypeKind.UINT,
                    TypeKind.ULONG,
                    TypeKind.ULONGLONG,
                    TypeKind.UINT128,
                    TypeKind.SHORT,
                    TypeKind.INT,
                    TypeKind.LONG,
                    TypeKind.LONGLONG,
                    TypeKind.INT128,
                ):
            out.write('int(')
            self.value.output(out)
            out.write(')')
        elif self.typekind in (
                    TypeKind.FLOAT,
                    TypeKind.DOUBLE,
                    TypeKind.LONGDOUBLE
                ):
            out.write('float(')
            self.value.output(out)
            out.write(')')
        else:
            self.value.output(out)

    def clean_argument(self):
        return self.value


class Invoke(Expression):
    def __init__(self, fn):
        self.fn = fn
        self.arguments = []

    def __repr__(self):
        return "<Invoke %s>" % self.fn

    def add_argument(self, argument):
        self.arguments.append(argument)

    def add_imports(self, context):
        self.fn.add_imports(context)
        for arg in self.arguments:
            arg.add_imports(context)

    def output(self, out):
        self.fn.output(out)
        out.write('(')
        if self.arguments:
            self.arguments[0].output(out)
            for arg in self.arguments[1:]:
                out.write(', ')
                arg.output(out)
        out.write(')')


class New(Expression):
    def __init__(self, typeref):
        self.typeref = typeref
        self.arguments = []

    def __repr__(self):
        return "<New %s>" % self.typeref

    def add_argument(self, argument):
        self.arguments.append(argument)

    def add_imports(self, context):
        self.typeref.add_imports(context)
        for arg in self.arguments:
            arg.add_imports(context)

    def output(self, out):
        self.typeref.output(out)
        out.write('(')
        if self.arguments:
            self.arguments[0].output(out)
            for arg in self.arguments[1:]:
                out.write(', ')
                arg.output(out)
        out.write(')')
