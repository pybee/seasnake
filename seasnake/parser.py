from __future__ import unicode_literals, print_function

import argparse
import os
import sys

from collections import namedtuple, OrderedDict

from clang.cindex import Index, Cursor, TypeKind, CursorKind, Type, TranslationUnit

if sys.version_info.major <= 2:
    text = unicode
else:
    text = str


def dump(node, depth=1):
    for name in dir(node):
        try:
            if not name.startswith('_') and name not in ('canonical',):
                attr = getattr(node, name)
                if isinstance(attr, (Cursor, Type)):
                    print("    " * depth + "%s:" % name)
                    dump(attr, depth + 1)
                else:
                    print("    " * depth + "%s = %s" % (name, attr))
                    if callable(attr):
                        try:
                            print("    " * (depth + 1) + "-> ", attr())
                        except:
                            print("    " * (depth + 1) + "-> CALL ERROR")
        except Exception as e:
            print("    " * depth + "%s = *%s*" % (name, e))


class Declaration(object):
    def __init__(self, parent=None, name=None):
        self.parent = parent
        self.name = name

        if self.parent is None:
            self.root = self
        else:
            self.root = self.parent.root

        if self.name and self.parent:
            self.parent.names[self.name] = self

    def __repr__(self):
        try:
            return "<%s %s>" % (self.__class__.__name__, self.full_name)
        except:
            return "<%s %s>" % (self.__class__.__name__, self.name)


class Context(Declaration):
    def __init__(self, parent=None, name=None):
        super(Context, self).__init__(parent=parent, name=name)
        self.names = OrderedDict()

    def __getitem__(self, name):
        # If the name is scoped, do a lookup from the root node.
        # Otherwise, just look up the name in the current context.
        if '::' in name:
            parts = name.split('::')
            decl = self.root
            for part in parts:
                decl = decl[part]
            return decl
        else:
            try:
                return self.names[name]
            except KeyError:
                if self.parent:
                    return self.parent.__getitem__(name)
                else:
                    raise


class Module(Context):
    def __init__(self, name, parent=None):
        super(Module, self).__init__(parent=parent, name=name)
        self.declarations = OrderedDict()
        self.imports = {}
        self.submodules = {}

    @property
    def full_name(self):
        if self.parent:
            return '::'.join([self.parent.full_name, self.name])
        return self.name

    def add_to_context(self, context):
        context.add_submodule(self)

    def add_declaration(self, decl):
        self.declarations[decl.name] = decl
        decl.add_imports(self)

    def add_import(self, path, symbol=None):
        self.imports.setdefault(path, set()).add(symbol)

    def add_imports(self, module):
        pass

    def add_submodule(self, module):
        self.submodules[module.name] = module

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
            out.clear_block()

        for name, decl in self.declarations.items():
            decl.output(out)


###########################################################################
# Enumerated types
###########################################################################

class Enumeration(Context):
    def __init__(self, parent, name):
        super(Enumeration, self).__init__(parent=parent, name=name)
        self.enumerators = []

    def add_enumerator(self, entry):
        self.enumerators.append(entry)

    def add_to_context(self, context):
        context.add_declaration(self)

    def add_imports(self, module):
        module.add_import('enum', 'Enum')

    def output(self, out, depth=0):
        out.write('    ' * depth + "class %s(Enum):\n" % self.name)
        if self.enumerators:
            for enumerator in self.enumerators:
                out.write('    ' * (depth + 1) + "%s = %s" % (
                    enumerator.key, enumerator.value
                ))
                out.clear_line()
        else:
            out.write('    pass')
            out.clear_line()
        out.clear_block()


EnumValue = namedtuple('EnumValue', ['key', 'value'])


###########################################################################
# Functions
###########################################################################

class Function(Context):
    def __init__(self, parent, name):
        super(Function, self).__init__(parent=parent, name=name)
        self.parameters = []
        self.statements = []

    def add_parameter(self, parameter):
        self.parameters.append(parameter)

    def add_to_context(self, context):
        context.add_declaration(self)

    def add_import(self, scope, name):
        self.parent.add_import(scope, name)

    def add_imports(self, module):
        pass

    def add_statement(self, statement):
        self.statements.append(statement)
        statement.add_imports(self)

    def output(self, out, depth=0):
        parameters = ', '.join(p.name for p in self.parameters)
        out.write('    ' * depth + "def %s(%s):\n" % (self.name, parameters))
        if self.statements:
            for statement in self.statements:
                out.write('    ' * (depth + 1))
                statement.output(out)
                out.clear_line()
        else:
            out.write('    pass')
        out.clear_block()


class Parameter(Declaration):
    def __init__(self, function, name, ctype, default):
        super(Parameter, self).__init__(parent=function, name=name)
        self.ctype = ctype
        self.default = default

    def add_to_context(self, context):
        context.add_parameter(self)


class Variable(Declaration):
    def __init__(self, parent, name, value=None):
        super(Variable, self).__init__(parent=parent, name=name)
        self.value = value

    def add_to_context(self, context):
        context.add_declaration(self)

    def add_imports(self, module):
        if self.value:
            self.value.add_imports(module)

    def output(self, out, depth=0):
        out.write('%s = ' % self.name)
        if self.value:
            self.value.output(out)
        else:
            out.write('None')
        out.clear_line()


###########################################################################
# Structs
###########################################################################

class Struct(Context):
    def __init__(self, parent, name):
        super(Struct, self).__init__(parent=parent, name=name)
        self.attributes = OrderedDict()

    def add_imports(self, module):
        pass

    def add_attribute(self, attr):
        self.attributes[attr.name] = attr

    def add_to_context(self, context):
        context.add_declaration(self)

    def output(self, out, depth=0):
        out.write('    ' * depth + "class %s:\n" % self.name)
        if self.attributes:
            params = ''.join(', %s=None' % name for name in self.attributes.keys())
            out.write('    ' * (depth + 1) + 'def __init__(self%s):\n' % params)
            for name, attr in self.attributes.items():
                out.write('    ' * (depth + 2))
                attr.output(out, init=True)
                out.clear_line()
        else:
            out.write('    ' * (depth + 1) + 'pass')
        out.clear_block()


# An attribute declaration
class Attribute(Declaration):
    def __init__(self, klass, name, value=None):
        super(Attribute, self).__init__(parent=klass, name=name)
        self.value = value

    def add_to_context(self, context):
        context.add_attribute(self)

    def add_imports(self, module):
        pass

    def output(self, out, init=False):
        out.write('self.%s = ' % self.name)
        if init:
            out.write(self.name)
        else:
            self.value.output(out)
        out.clear_line()


###########################################################################
# Unions
###########################################################################

class Union(Context):
    def __init__(self, parent, name):
        super(Union, self).__init__(parent=parent, name=name)
        self.attributes = OrderedDict()

    def add_imports(self, module):
        pass

    def add_attribute(self, attr):
        self.attributes[attr.name] = attr

    def add_to_context(self, context):
        context.add_declaration(self)

    def output(self, out, depth=0):
        out.write('    ' * depth + "class %s:\n" % self.name)
        if self.attributes:
            params = ''.join(', %s=None' % name for name in self.attributes.keys())
            out.write('    ' * (depth + 1) + 'def __init__(self%s):\n' % params)
            for name, attr in self.attributes.items():
                out.write('    ' * (depth + 2))
                attr.output(out, init=True)
                out.clear_line()
        else:
            out.write('    ' * (depth + 1) + 'pass')
        out.clear_block()


###########################################################################
# Classes
###########################################################################

class Class(Context):
    def __init__(self, parent, name):
        super(Class, self).__init__(parent=parent, name=name)
        self.superclass = None
        self.constructor = None
        self.destructor = None
        self.attributes = OrderedDict()
        self.methods = OrderedDict()
        self.classes = OrderedDict()

    def add_imports(self, module):
        if self.superclass:
            pass

    def add_declaration(self, klass):
        self.classes.append(klass)

    def add_constructor(self, method):
        if self.constructor:
            if self.constructor.statements is None:
                self.constructor = method
            else:
                raise Exception("Cannot handle multiple constructors")
        else:
            self.constructor = method

    def add_destructor(self, method):
        if self.destructor:
            if self.destructor.statements is None:
                self.destructor = method
            else:
                raise Exception("Cannot handle multiple destructors")
        else:
            self.destructor = method

    def add_attribute(self, attr):
        self.attributes[attr.name] = attr

    def add_method(self, method):
        self.methods[method.name] = method

    def add_to_context(self, context):
        context.add_declaration(self)

    def output(self, out, depth=0):
        if self.superclass:
            out.write('    ' * depth + "class %s(%s):\n" % (self.name, self.superclass))
        else:
            out.write('    ' * depth + "class %s:\n" % self.name)
        if self.constructor or self.destructor or self.methods:
            if self.constructor:
                self.constructor.output(out, depth + 1)

            if self.destructor:
                self.destructor.output(out, depth + 1)

            for name, method in self.methods.items():
                method.output(out, depth + 1)
        else:
            out.write('    ' * (depth + 1) + 'pass')
        out.clear_block()


class Constructor(Context):
    def __init__(self, klass):
        super(Constructor, self).__init__(parent=klass)
        self.parameters = []
        self.statements = None

    def add_parameter(self, parameter):
        self.parameters.append(parameter)

    def add_to_context(self, klass):
        self.parent.add_constructor(self)

    def add_attribute(self, attr):
        self.parent.add_attribute(attr)

    def add_imports(self, module):
        pass

    def add_statement(self, statement):
        if self.statements:
            self.statements.append(statement)
        else:
            self.statements = [statement]
        statement.add_imports(self)

    def output(self, out, depth=0):
        if self.parameters:
            parameters = ', '.join(
                p.name if p.name else 'arg%s' % (i + 1)
                for i, p in enumerate(self.parameters))
            out.write('    ' * depth + "def __init__(self, %s):\n" % parameters)
        else:
            out.write('    ' * depth + "def __init__(self):\n")
        if self.parent.attributes or self.statements:
            has_init = False
            for name, attr in self.parent.attributes.items():
                if attr.value is not None:
                    out.write('    ' * (depth + 1))
                    attr.output(out)
                    out.clear_line()
                    has_init = True

            if self.statements:
                for statement in self.statements:
                    out.write('    ' * (depth + 1))
                    statement.output(out)
                    out.clear_line()
            elif not has_init:
                out.write('    ' * (depth + 1) + 'pass')
                out.clear_line()

        else:
            out.write('    ' * (depth + 1) + 'pass')
        out.clear_block(blank_lines=1)


class Destructor(Context):
    def __init__(self, klass):
        super(Destructor, self).__init__(parent=klass)
        self.parameters = []
        self.statements = None

    def add_to_context(self, klass):
        self.parent.add_destructor(self)

    def add_imports(self, module):
        pass

    def add_statement(self, statement):
        if self.statements:
            self.statements.append(statement)
        else:
            self.statements = [statement]
        statement.add_imports(self)

    def output(self, out, depth=0):
        out.write('    ' * depth + "def __del__(self):\n")
        if self.statements:
            for statement in self.statements:
                out.write('    ' * (depth + 1))
                statement.output(out)
                out.clear_line()
        else:
            out.write('    ' * (depth + 1) + 'pass')
        out.clear_block(blank_lines=1)


# An instance method on a class.
class Method(Context):
    def __init__(self, klass, name, pure_virtual):
        super(Method, self).__init__(parent=klass, name=name)
        self.parameters = []
        self.statements = None
        self.pure_virtual = pure_virtual

    def add_parameter(self, parameter):
        self.parameters.append(parameter)

    def add_to_context(self, context):
        self.parent.add_method(self)

    def add_imports(self, module):
        pass

    def add_statement(self, statement):
        if self.statements:
            self.statements.append(statement)
        else:
            self.statements = [statement]
        statement.add_imports(self)

    def output(self, out, depth=0):
        if self.parameters:
            parameters = ', '.join(p.name for p in self.parameters)
            out.write('    ' * depth + "def %s(self, %s):\n" % (self.name, parameters))
        else:
            out.write('    ' * depth + "def %s(self):\n" % self.name)
        if self.statements:
            for statement in self.statements:
                out.write('    ' * (depth + 1))
                statement.output(out)
                out.clear_line()
        elif self.pure_virtual:
            out.write('    ' * (depth + 1) + 'raise NotImplementedError()')
        else:
            out.write('    ' * (depth + 1) + 'pass')
        out.clear_block(blank_lines=1)


###########################################################################
# Statements
###########################################################################

class Return(object):
    def __init__(self):
        self.value = None

    def add_imports(self, module):
        pass

    def add_expression(self, expr):
        self.value = expr

    def output(self, out, depth=0):
        out.write('return')
        if self.value:
            out.write(' ')
            self.value.output(out)
            out.clear_line()


###########################################################################
# Expressions
###########################################################################

# A reference to a variable
class Reference(object):
    def __init__(self, ref, node):
        parts = ref.split('::')
        self.scope = parts[:-1]
        self.name = parts[-1]
        self.node = node

    def add_imports(self, module):
        if self.scope:
            module.add_import('.'.join(self.scope), self.name)

    def output(self, out):
        out.write(self.name)


# A reference to self.
class SelfReference(object):
    def add_imports(self, module):
        pass

    def output(self, out):
        out.write('self')


# A reference to an attribute on a class
class AttributeReference(object):
    def __init__(self, instance, attr):
        self.instance = instance
        self.attr = attr

    # def add_to_context(self, context):
    #     pass

    def add_imports(self, module):
        pass

    def output(self, out):
        self.instance.output(out)
        out.write('.%s' % self.attr)


class Literal(object):
    def __init__(self, value):
        self.value = value

    def add_imports(self, module):
        pass

    def output(self, out):
        out.write(text(self.value))


class ListLiteral(object):
    def __init__(self):
        self.value = []

    def add_imports(self, module):
        for value in self.value:
            value.add_imports(module)

    def append(self, item):
        self.value.append(item)

    def output(self, out):
        out.write('[')
        for i, item in enumerate(self.value):
            if i != 0:
                out.write(', ')
            item.output(out)
        out.write(']')


class UnaryOperation(object):
    def __init__(self, op, value):
        self.op = op
        self.value = value

    def add_imports(self, module):
        self.value.add_imports(module)

    def output(self, out):
        out.write(self.op)
        self.value.output(out)


class BinaryOperation(object):
    def __init__(self, lvalue, op, rvalue):
        self.lvalue = lvalue
        self.op = op
        self.rvalue = rvalue

    def add_imports(self, module):
        self.lvalue.add_imports(module)
        self.rvalue.add_imports(module)

    def output(self, out):
        self.lvalue.output(out)
        out.write(' %s ' % self.op)
        self.rvalue.output(out)


class ConditionalOperation(object):
    def __init__(self, condition, true_result, false_result):
        self.condition = condition
        self.true_result = true_result
        self.false_result = false_result

    def add_imports(self, module):
        self.true_result.add_imports(module)
        self.false_result.add_imports(module)

    def output(self, out):
        out.write('(')
        self.true_result.output(out)
        out.write(' if ')
        self.condition.output(out)
        out.write(' else ')
        self.false_result.output(out)
        out.write(')')


class Parentheses(object):
    def __init__(self, body):
        self.body = body

    def add_imports(self, module):
        self.body.add_imports(module)

    def output(self, out):
        if isinstance(self.body, (BinaryOperation, ConditionalOperation)):
            out.write('(')
            self.body.output(out)
            out.write(')')
        else:
            self.body.output(out)


class ArraySubscript(object):
    def __init__(self, value, index):
        self.value = value
        self.index = index

    def add_imports(self, module):
        self.value.add_imports(module)
        self.index.add_imports(module)

    def output(self, out):
        self.value.output(out)
        out.write('[')
        self.index.output(out)
        out.write(']')


class CastOperation(object):
    def __init__(self, typekind, value):
        self.typekind = typekind
        self.value = value

    def add_imports(self, module):
        self.value.add_imports(module)

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


class FunctionCall(object):
    def __init__(self, fn):
        self.fn = fn
        self.arguments = []

    def add_argument(self, argument):
        self.arguments.append(argument)

    def add_imports(self, module):
        self.fn.add_imports(module)
        for arg in self.arguments:
            arg.add_imports(module)

    def output(self, out):
        self.fn.output(out)
        out.write('(')
        if self.arguments:
            self.arguments[0].output(out)
            for arg in self.arguments[1:]:
                out.write(', ')
                arg.output(out)
        out.write(')')


class New(object):
    def __init__(self, typeref):
        self.typeref = typeref
        self.arguments = []

    def add_argument(self, argument):
        self.arguments.append(argument)

    def add_imports(self, module):
        self.typeref.add_imports(module)
        for arg in self.arguments:
            arg.add_imports(module)

    def output(self, out):
        out.write('%s(' % self.typeref.name)
        if self.arguments:
            self.arguments[0].output(out)
            for arg in self.arguments[1:]:
                out.write(', ')
                arg.output(out)
        out.write(')')


###########################################################################
# Code Writer
#
# This is a helper that can be used to write code; it knows how to
# maintain the right number of spaces between code blocks to remain PEP8
# compliant.
###########################################################################

class CodeWriter(object):
    def __init__(self, out):
        self.out = out
        self.line_cleared = True
        self.block_cleared = 2

    def write(self, content):
        self.out.write(content)
        self.line_cleared = False
        self.block_cleared = 0

    def clear_line(self):
        if not self.line_cleared:
            self.out.write('\n')
            self.line_cleared = True

    def clear_block(self, blank_lines=2):
        self.clear_line()
        while self.block_cleared < blank_lines:
            self.out.write('\n')
            self.block_cleared += 1


###########################################################################
# Code Parser
###########################################################################

class BaseParser(object):
    def __init__(self):
        self.index = Index.create()

    def diagnostics(self, out):
        for diag in self.tu.diagnostics:
            print('%s %s (line %s, col %s) %s' % (
                    {
                        4: 'FATAL',
                        3: 'ERROR',
                        2: 'WARNING',
                        1: 'NOTE',
                        0: 'IGNORED',
                    }[diag.severity],
                    diag.location.file,
                    diag.location.line,
                    diag.location.column,
                    diag.spelling
                ), file=out)


class CodeConverter(BaseParser):
    def __init__(self, name):
        super(CodeConverter, self).__init__()
        self.root_module = Module(name)
        self.filenames = set()
        self.macros = {}
        self.instantiated_macros = {}

        self.ignored_files = set()

    def output(self, module, out):
        module_path = module.split('.')

        mod = None
        for i, mod_name in enumerate(module_path):
            if mod is None:
                mod = self.root_module
            else:
                mod = mod.submodules[mod_name]

            if mod_name != mod.name:
                raise Exception("Unknown module '%s'" % '.'.join(module_path[:i+1]))

        if mod:
            mod.output(CodeWriter(out))
        else:
            raise Exception('No module name specified')

    def _output_module(self, mod, out):
        out.write('===== %s.py ==================================================\n' % mod.full_name)
        mod.output(CodeWriter(out))
        for submodule in mod.submodules.values():
            self._output_module(submodule, out)

    def output_all(self, out):
        self._output_module(self.root_module, out)

    def parse(self, filename, flags):
        self.filenames.add(os.path.abspath(filename))
        self.tu = self.index.parse(
            None,
            args=[filename] + flags,
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        )
        self.handle(self.tu.cursor, self.root_module)

    def parse_text(self, files, flags):
        self.filenames.add(*[os.path.abspath(filename) for filename, content in files])
        self.tu = self.index.parse(
            files[0][0],
            args=flags,
            unsaved_files=files,
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        )
        self.handle(self.tu.cursor, self.root_module)

    def handle(self, node, context=None):
        if (node.location.file is None
                or os.path.abspath(node.location.file.name) in self.filenames
                or os.path.splitext(node.location.file.name)[1] in ('.h', '.hpp', '.hxx')):
            try:
                # print(node.kind, node.type.kind, node.spelling, node.location.file)
                handler = getattr(self, 'handle_%s' % node.kind.name.lower())
            except AttributeError:
                print("Ignoring node of type %s" % node.kind, file=sys.stderr)
                handler = None
        else:
            if '/usr/include/c++/v1' not in node.location.file.name:
                if node.location.file.name not in self.ignored_files:

                    print("Ignoring node in file %s" % node.location.file, file=sys.stderr)
                    self.ignored_files.add(node.location.file.name)
            handler = None

        if handler:
            return handler(node, context)

    def handle_unexposed_decl(self, node, context):
        # Ignore unexposed declarations (e.g., friend qualifiers)
        pass

    def handle_struct_decl(self, node, context):
        struct = Struct(context, node.spelling)
        for child in node.get_children():
            decl = self.handle(child, struct)
            if decl:
                decl.add_to_context(struct)
        return struct

    def handle_union_decl(self, node, context):
        union = Union(context, node.spelling)
        for child in node.get_children():
            decl = self.handle(child, union)
            if decl:
                decl.add_to_context(union)
        return union

    def handle_class_decl(self, node, context):
        klass = Class(context, node.spelling)
        for child in node.get_children():
            decl = self.handle(child, klass)
            if decl:
                decl.add_to_context(klass)
        return klass

    def handle_enum_decl(self, node, context):
        enum = Enumeration(context, node.spelling)
        for child in node.get_children():
            enum.add_enumerator(self.handle(child, enum))
        return enum

    def handle_field_decl(self, node, context):
        try:
            children = node.get_children()
            child = next(children)
            if child.kind == CursorKind.TYPE_REF:
                value = None
            else:
                value = self.handle(child, context)
            attr = Attribute(context, node.spelling, value)
        except StopIteration:
            attr = Attribute(context, node.spelling, None)

        try:
            next(children)
            raise Exception("Field declaration has > 1 child node.")
        except StopIteration:
            pass

        return attr

    def handle_enum_constant_decl(self, node, enum):
        return EnumValue(node.spelling, node.enum_value)

    def handle_function_decl(self, node, context):
        function = Function(context, node.spelling)

        children = node.get_children()
        # If the return type is RECORD, then the first
        # child will be a TYPE_REF for that class; skip it
        if node.result_type.kind in (TypeKind.RECORD, TypeKind.LVALUEREFERENCE, TypeKind.POINTER):
            next(children)

        for child in children:
            decl = self.handle(child, function)
            if decl:
                decl.add_to_context(function)
        return function

    def handle_var_decl(self, node, context):
        try:
            children = node.get_children()
            # If this is a node of type RECORD, then the first node will be a
            # type declaration; we can ignore that node. If that first node is
            # a namespace refernce, we can discard the  second node as well.
            if node.type.kind in (TypeKind.RECORD, TypeKind.POINTER):
                child = next(children)
                while child.kind == CursorKind.NAMESPACE_REF:
                    child = next(children)

            value = self.handle(next(children), context)

            # Array definitions put the array size first.
            # If there is a child, discard the value and
            # replace it with the list declaration.
            try:
                value = self.handle(next(children), context)
            except StopIteration:
                pass

            return Variable(context, node.spelling, value)
        except StopIteration:
            return None
            # Alternatively; explicitly set to None
            # return Variable(context, node.spelling)

    def handle_parm_decl(self, node, function):
        # FIXME: need to pay attention to parameter declarations
        # that include an assignment (i.e., a default argument value).
        return Parameter(function, node.spelling, None, None)

    def handle_typedef_decl(self, node, context):
        # Typedefs aren't needed, so ignore them
        pass

    def handle_cxx_method(self, node, context):
        # If this is an inline method, the context will be the
        # enclosing class, and the inline declaration will double as the
        # prototype.
        #
        # If it isn't inline, the context will be a module, and the
        # prototype will be separate. In this case, the method will
        # be found  twice - once as the prototype, and once as the
        # definition.  Parameters are handled as part of the prototype;
        # this handle method only returns a new node when it finds the
        # prototype. When the body method is encountered, it finds the
        # prototype method (which will be the TYPE_REF in the first
        # child node), and adds the body definition.
        if isinstance(context, Class):
            method = Method(context, node.spelling, node.is_pure_virtual_method())
            is_prototype = True
        else:
            method = None
            is_prototype = False

        children = node.get_children()

        # If the return type is RECORD, then the first child will be a
        # TYPE_REF describing the return type; that node can be skipped.
        if node.result_type.kind in (TypeKind.RECORD, TypeKind.LVALUEREFERENCE):
            next(children)

        for child in children:
            decl = self.handle(child, method)
            if method is None:
                # First node will be a TypeRef for the class.
                # Use this to get the method.
                method = context[decl.name].methods[node.spelling]
            elif decl:
                if is_prototype or child.kind != CursorKind.PARM_DECL:
                    decl.add_to_context(method)

        # Only add a new node for the prototype.
        if is_prototype:
            return method

    def handle_namespace(self, node, module):
        submodule = Module(node.spelling, parent=module)
        for child in node.get_children():
            decl = self.handle(child, submodule)
            if decl:
                decl.add_to_context(submodule)
        return submodule

    # def handle_linkage_spec(self, node, context):
    def handle_constructor(self, node, context):
        # If this is an inline constructor, the context will be the
        # enclosing class, and the inline declaration will double as the
        # prototype.
        #
        # If it isn't inline, the context will be a module, and the
        # prototype will be separate. In this case, the constructor will
        # be found  twice - once as the prototype, and once as the
        # definition.  Parameters are handled as part of the prototype;
        # this handle method only returns a new node when it finds the
        # prototype. When the body method is encountered, it finds the
        # prototype constructor (which will be the TYPE_REF in the first
        # child node), and adds the body definition.
        if isinstance(context, Class):
            constructor = Constructor(context)
            is_prototype = True
        else:
            constructor = None
            is_prototype = False

        for child in node.get_children():
            decl = self.handle(child, constructor)
            if constructor is None:
                # First node will be a TypeRef for the class.
                # Use this to get the constructor
                constructor = context[decl.name].constructor
            elif decl:
                if is_prototype or child.kind != CursorKind.PARM_DECL:
                    decl.add_to_context(constructor)

        # Only add a new node for the prototype.
        if is_prototype:
            return constructor

    def handle_destructor(self, node, context):
        # If this is an inline destructor, the context will be the
        # enclosing class, and the inline declaration will double as the
        # prototype.
        #
        # If it isn't inline, the context will be a module, and the
        # prototype will be separate. In this case, the destructor will
        # be found  twice - once as the prototype, and once as the
        # definition.  Parameters are handled as part of the prototype;
        # this handle method only returns a new node when it finds the
        # prototype. When the body method is encountered, it finds the
        # prototype destructor (which will be the TYPE_REF in the first
        # child node), and adds the body definition.

        if isinstance(context, Class):
            destructor = Destructor(context)
            is_prototype = True
        else:
            destructor = None
            is_prototype = False

        for child in node.get_children():
            decl = self.handle(child, destructor)
            if destructor is None:
                # First node will be a TypeRef for the class.
                # Use this to get the destructor
                destructor = context[decl.name].destructor
            elif decl:
                if is_prototype or child.kind != CursorKind.PARM_DECL:
                    decl.add_to_context(destructor)

        # Only add a new node for the prototype.
        if is_prototype:
            return destructor

    # def handle_conversion_function(self, node, context):
    # def handle_template_type_parameter(self, node, context):
    # def handle_template_non_type_parameter(self, node, context):
    # def handle_template_template_parameter(self, node, context):
    # def handle_function_template(self, node, context):
    # def handle_class_template(self, node, context):
    # def handle_class_template_partial_specialization(self, node, context):
    # def handle_namespace_alias(self, node, context):
    # def handle_using_directive(self, node, context):
    # def handle_using_declaration(self, node, context):
    # def handle_type_alias_decl(self, node, context):

    def handle_cxx_access_spec_decl(self, node, context):
        # Ignore access specifiers; everything is public.
        pass

    def handle_type_ref(self, node, context):
        typename = node.spelling.split()[-1]
        return Reference(typename, node)

    def handle_cxx_base_specifier(self, node, context):
        context.superclass = node.spelling.split(' ')[1]

    # def handle_template_ref(self, node, context):

    def handle_namespace_ref(self, node, context):
        # Namespace references are handled by type scoping
        pass

    def handle_member_ref(self, node, context):
        try:
            children = node.get_children()
            child = next(children)
            ref = AttributeReference(self.handle(child, context), node.spelling)
        except StopIteration:
            # An implicit reference to `this`
            ref = AttributeReference(SelfReference(), node.spelling)

        try:
            next(children)
            raise Exception("Member reference has > 1 child node.")
        except StopIteration:
            pass
        return ref

    # def handle_label_ref(self, node, context):
    # def handle_overloaded_decl_ref(self, node, context):
    # def handle_variable_ref(self, node, context):
    # def handle_invalid_file(self, node, context):
    # def handle_no_decl_found(self, node, context):
    # def handle_not_implemented(self, node, context):
    # def handle_invalid_code(self, node, context):

    def handle_unexposed_expr(self, node, statement):
        # Ignore unexposed nodes; pass whatever is the first
        # (and should be only) child unaltered.
        try:
            children = node.get_children()
            expr = self.handle(next(children), statement)
        except StopIteration:
            raise Exception("Unexposed expression has no children.")

        try:
            next(children)
            raise Exception("Unexposed expression has > 1 children.")
        except StopIteration:
            pass

        return expr

    def handle_decl_ref_expr(self, node, statement):
        return Reference(node.spelling, node)

    def handle_member_ref_expr(self, node, context):
        try:
            children = node.get_children()
            first_child = next(children)
            ref = AttributeReference(self.handle(first_child, context), node.spelling)
        except StopIteration:
            # An implicit reference to `this`
            ref = AttributeReference(SelfReference(), node.spelling)

        try:
            next(children)
            raise Exception("Member reference expression has > 1 children.")
        except StopIteration:
            pass

        return ref

    def handle_call_expr(self, node, context):
        try:
            children = node.get_children()
            first_child = self.handle(next(children))
            if (isinstance(first_child, Reference) and (
                    first_child.node.type.kind == TypeKind.FUNCTIONPROTO
                    )) or isinstance(first_child, AttributeReference):

                fn = FunctionCall(first_child)

                for child in children:
                    fn.add_argument(self.handle(child, context))

                return fn
            else:
                # Implicit cast or functional cast
                return first_child
        except StopIteration:
            FunctionCall(node.spelling)

    # def handle_block_expr(self, node, context):

    def handle_integer_literal(self, node, context):
        try:
            content = next(node.get_tokens()).spelling
        except StopIteration:
            # No tokens on the node;
            content = self.instantiated_macros[
                (node.location.file.name, node.location.line, node.location.column)
            ]

        if content.startswith('0x'):
            int(content, 16)
        elif content.startswith('0'):
            int(content, 8)
        else:
            int(content)

        return Literal(content)

    def handle_floating_literal(self, node, context):
        try:
            content = next(node.get_tokens()).spelling
        except StopIteration:
            content = self.instantiated_macros[
                (node.location.file.name, node.location.line, node.location.column)
            ]

        return Literal(float(content))

    # def handle_imaginary_literal(self, node, context):

    def handle_string_literal(self, node, context):
        try:
            content = next(node.get_tokens()).spelling
        except StopIteration:
            content = self.instantiated_macros[
                (node.location.file.name, node.location.line, node.location.column)
            ]

        return Literal(content)

    def handle_character_literal(self, node, context):
        try:
            content = next(node.get_tokens()).spelling
        except StopIteration:
            content = self.instantiated_macros[
                (node.location.file, node.location.line, node.location.column)
            ]

        return Literal(content)

    def handle_paren_expr(self, node, context):
        try:
            children = node.get_children()
            parens = Parentheses(self.handle(next(children), context))
        except StopIteration:
            raise Exception("Parentheses must contain an expression.")

        try:
            next(children)
            raise Exception("Parentheses can only contain one expression.")
        except StopIteration:
            pass

        return parens

    def handle_unary_operator(self, node, context):
        try:
            children = node.get_children()
            child = next(children)

            operand = list(node.get_tokens())[0].spelling
            # Dereferencing operator is a pass through.
            # All others must be processed as defined.
            if operand == '*':
                unaryop = self.handle(child, context)
            else:
                op = operand
                value = self.handle(child, context)

                unaryop = UnaryOperation(op, value)
        except StopIteration:
            raise Exception("Unary expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Unary expression has > 1 child node.")
        except StopIteration:
            pass

        return unaryop

    def handle_array_subscript_expr(self, node, context):
        try:
            children = node.get_children()

            subject = self.handle(next(children), context)
            index = self.handle(next(children), context)
            value = ArraySubscript(subject, index)
        except StopIteration:
            raise Exception("Array subscript requires 2 child nodes.")

        try:
            next(children)
            raise Exception("Array subscript has > 2 child nodes.")
        except StopIteration:
            pass

        return value

    def handle_binary_operator(self, node, context):
        try:
            children = node.get_children()

            lnode = next(children)
            lvalue = self.handle(lnode, context)

            op = list(lnode.get_tokens())[-1].spelling

            rnode = next(children)
            rvalue = self.handle(rnode, context)

            binop = BinaryOperation(lvalue, op, rvalue)
        except StopIteration:
            raise Exception("Binary operator requires 2 child nodes.")

        try:
            next(children)
            raise Exception("Binary operator has > 2 child nodes.")
        except StopIteration:
            pass

        return binop

    # def handle_compound_assignment_operator(self, node, context):
    def handle_conditional_operator(self, node, context):
        try:
            children = node.get_children()

            true_value = self.handle(next(children), context)
            condition = self.handle(next(children), context)
            false_value = self.handle(next(children), context)

            condop = ConditionalOperation(condition, true_value, false_value)
        except StopIteration:
            raise Exception("Conditional operator requires 3 child nodes.")

        try:
            next(children)
            raise Exception("Conditional operator has > 3 child nodes.")
        except StopIteration:
            pass

        return condop

    def handle_cstyle_cast_expr(self, node, context):
        try:
            children = node.get_children()
            child = next(children)

            cast = CastOperation(node.type.kind, self.handle(child, context))
        except StopIteration:
            raise Exception("Cast expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Cast expression has > 1 child node.")
        except StopIteration:
            pass

        return cast

    def handle_init_list_expr(self, node, context):
        children = node.get_children()

        value = ListLiteral()
        for child in children:
            value.append(self.handle(child, context))

        return value

    # def handle_addr_label_expr(self, node, context):
    # def handle_stmtexpr(self, node, context):
    # def handle_generic_selection_expr(self, node, context):
    # def handle_gnu_null_expr(self, node, context):
    # def handle_cxx_static_cast_expr(self, node, context):
    # def handle_cxx_dynamic_cast_expr(self, node, context):
    # def handle_cxx_reinterpret_cast_expr(self, node, context):
    # def handle_cxx_const_cast_expr(self, node, context):
    def handle_cxx_functional_cast_expr(self, node, context):
        try:
            children = node.get_children()

            fn = FunctionCall(self.handle(next(children), context))
            fn.add_argument(self.handle(next(children), context))
        except StopIteration:
            raise Exception("Functional cast requires 2 child nodes.")

        try:
            next(children)
            raise Exception("Functional cast has > 2 child nodes.")
        except StopIteration:
            pass

        return fn

    # def handle_cxx_typeid_expr(self, node, context):
    # def handle_cxx_bool_literal_expr(self, node, context):
    def handle_cxx_this_expr(self, node, context):
        return SelfReference()

    # def handle_cxx_throw_expr(self, node, context):
    def handle_cxx_new_expr(self, node, context):
        children = node.get_children()

        # The first child might be a namespace reference. If it is,
        # we can ignore it. The child after the namespace (or the
        # first child, if no namespace exists) is the type definition
        # for the class to be instantiated.
        child = next(children)
        while child.kind == CursorKind.NAMESPACE_REF:
            child = next(children)

        new = New(self.handle(child, context))

        for arg in next(children).get_children():
            new.add_argument(self.handle(arg, context))

        return new

    # def handle_cxx_delete_expr(self, node, context):
    # def handle_cxx_unary_expr(self, node, context):
    # def handle_pack_expansion_expr(self, node, context):
    # def handle_size_of_pack_expr(self, node, context):
    # def handle_lambda_expr(self, node, context):
    # def handle_unexposed_stmt(self, node, context):
    # def handle_label_stmt(self, node, context):

    def handle_compound_stmt(self, node, context):
        for child in node.get_children():
            statement = self.handle(child, context)
            if statement:
                context.add_statement(statement)

    # def handle_case_stmt(self, node, context):
    # def handle_default_stmt(self, node, context):
    # def handle_if_stmt(self, node, context):
    # def handle_switch_stmt(self, node, context):
    # def handle_while_stmt(self, node, context):
    # def handle_do_stmt(self, node, context):
    # def handle_for_stmt(self, node, context):
    # def handle_goto_stmt(self, node, context):
    # def handle_indirect_goto_stmt(self, node, context):
    # def handle_continue_stmt(self, node, context):
    # def handle_break_stmt(self, node, context):
    def handle_return_stmt(self, node, context):
        retval = Return()
        try:
            retval.value = self.handle(next(node.get_children()), context)
        except StopIteration:
            pass

        return retval

    # def handle_asm_stmt(self, node, context):
    # def handle_cxx_catch_stmt(self, node, context):
    # def handle_cxx_try_stmt(self, node, context):
    # def handle_cxx_for_range_stmt(self, node, context):
    # def handle_seh_try_stmt(self, node, context):
    # def handle_seh_except_stmt(self, node, context):
    # def handle_seh_finally_stmt(self, node, context):
    # def handle_ms_asm_stmt(self, node, context):
    # def handle_null_stmt(self, node, context):
    def handle_decl_stmt(self, node, context):
        try:
            statement = self.handle(next(node.get_children()), context)
        except StopIteration:
            pass

        try:
            self.handle(next(node.get_children()), context)
        except StopIteration:
            raise Exception("Don't know how to handle multiple statements")

        return statement

    def handle_translation_unit(self, node, tu):
        for child in node.get_children():
            decl = self.handle(child, tu)
            if decl:
                decl.add_to_context(tu)

    # def handle_unexposed_attr(self, node, context):
    # def handle_ib_action_attr(self, node, context):
    # def handle_ib_outlet_attr(self, node, context):
    # def handle_ib_outlet_collection_attr(self, node, context):
    # def handle_cxx_final_attr(self, node, context):
    # def handle_cxx_override_attr(self, node, context):
    # def handle_annotate_attr(self, node, context):
    # def handle_asm_label_attr(self, node, context):
    # def handle_packed_attr(self, node, context):
    # def handle_pure_attr(self, node, context):
    # def handle_const_attr(self, node, context):
    # def handle_noduplicate_attr(self, node, context):
    # def handle_cudaconstant_attr(self, node, context):
    # def handle_cudadevice_attr(self, node, context):
    # def handle_cudaglobal_attr(self, node, context):
    # def handle_cudahost_attr(self, node, context):
    # def handle_cudashared_attr(self, node, context):
    # def handle_visibility_attr(self, node, context):
    # def handle_dllexport_attr(self, node, context):
    # def handle_dllimport_attr(self, node, context):
    # def handle_preprocessing_directive(self, node, context):

    def handle_macro_definition(self, node, context):
        tokens = node.get_tokens()
        key = next(tokens).spelling
        value = next(tokens).spelling
        self.macros[key] = value

    def handle_macro_instantiation(self, node, context):
        self.instantiated_macros[
            (node.location.file.name, node.location.line, node.location.column)
        ] = self.macros.get(node.spelling, '')

    def handle_inclusion_directive(self, node, context):
        # Ignore inclusion directives
        pass

    # def handle_module_import_decl(self, node, context):
    # def handle_type_alias_template_decl(self, node, context):

    ############################################################
    # Objective-C methods
    # If an algorithm exists in Objective C, implementing these
    # methods will allow conversion of that code.
    ############################################################
    # def handle_objc_synthesize_decl(self, node, context):
    # def handle_objc_dynamic_decl(self, node, context):
    # def handle_objc_super_class_ref(self, node, context):
    # def handle_objc_protocol_ref(self, node, context):
    # def handle_objc_class_ref(self, node, context):
    # def handle_objc_message_expr(self, node, context):
    # def handle_objc_string_literal(self, node, context):
    # def handle_objc_encode_expr(self, node, context):
    # def handle_objc_selector_expr(self, node, context):
    # def handle_objc_protocol_expr(self, node, context):
    # def handle_objc_bridge_cast_expr(self, node, context):
    # def handle_obj_bool_literal_expr(self, node, context):
    # def handle_obj_self_expr(self, node, context):
    # def handle_objc_at_try_stmt(self, node, context):
    # def handle_objc_at_catch_stmt(self, node, context):
    # def handle_objc_at_finally_stmt(self, node, context):
    # def handle_objc_at_throw_stmt(self, node, context):
    # def handle_objc_at_synchronized_stmt(self, node, context):
    # def handle_objc_autorelease_pool_stmt(self, node, context):
    # def handle_objc_for_collection_stmt(self, node, context):
    # def handle_objc_interface_decl(self, node, context):
    # def handle_objc_category_decl(self, node, context):
    # def handle_objc_protocol_decl(self, node, context):
    # def handle_objc_property_decl(self, node, context):
    # def handle_objc_ivar_decl(self, node, context):
    # def handle_objc_instance_method_decl(self, node, context):
    # def handle_objc_class_method_decl(self, node, context):
    # def handle_objc_implementation_decl(self, node, context):
    # def handle_objc_category_impl_decl(self, node, context):


# A simpler version of Parser that just
# dumps the tree structure.
class CodeDumper(BaseParser):
    def parse(self, filename, flags):
        self.tu = self.index.parse(
            None,
            args=[filename] + flags,
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        )
        self.diagnostics(sys.stderr)

        print('===', filename)
        self.handle(self.tu.cursor, 0)

    def handle(self, node, depth=0):
        print(
            '    ' * depth,
            node.kind,
            '(type:%s | result type:%s)' % (node.type.kind, node.result_type.kind),
            node.spelling,
        )

        for child in node.get_children():
            self.handle(child, depth + 1)

if __name__ == '__main__':
    opts = argparse.ArgumentParser(
        description='Display AST structure for C++ file.',
    )

    opts.add_argument(
        '-I', '--include',
        dest='includes',
        metavar='/path/to/includes',
        help='A directory of includes',
        action='append',
        default=[]
    )

    opts.add_argument(
        '-D',
        dest='defines',
        metavar='SYMBOL',
        help='Preprocessor symbols to use',
        action='append',
        default=[]
    )

    opts.add_argument(
        'filename',
        metavar='file.cpp',
        help='The file(s) to dump.',
        nargs="+"
    )

    args = opts.parse_args()

    dumper = CodeDumper()
    for filename in args.filename:
        dumper.parse(
            filename,
            flags=[
                '-I%s' % inc for inc in args.includes
            ] + [
                '-D%s' % define for define in args.defines
            ]
        )
