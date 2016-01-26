###########################################################################
# Code Parser
#
# This uses the clang Python API to parse and traverse the AST for C++
# code, producing a data model.
###########################################################################
from __future__ import unicode_literals, print_function

import argparse
import os
import sys

from clang.cindex import Index, TypeKind, CursorKind, TranslationUnit

from .model import *
from .writer import CodeWriter


# Python 2 compatibility shims
if sys.version_info.major <= 2:
    text = unicode
else:
    text = str


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
    def __init__(self, name, verbosity=0):
        super(CodeConverter, self).__init__()
        # Tools for debugging.
        self.verbosity = verbosity
        self._depth = 0

        self.root_module = Module(name)
        self.filenames = set()
        self.macros = {}
        self.instantiated_macros = {}

        self.ignored_files = set()
        self.last_decl = []

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

    def parse_text(self, filename, content, flags):
        self.filenames.add(os.path.abspath(filename))

        self.tu = self.index.parse(
            filename,
            args=flags,
            unsaved_files=[(filename, content)],
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        )
        self.handle(self.tu.cursor, self.root_module)

    def handle(self, node, context=None, tokens=None):
        if (node.location.file is None
                or os.path.abspath(node.location.file.name) in self.filenames
                or (
                    os.path.splitext(node.location.file.name)[1] in ('.h', '.hpp', '.hxx')
                    and '/usr/include' not in node.location.file.name)):
            try:
                if ((node.location.file or node.kind == CursorKind.TRANSLATION_UNIT) and self.verbosity > 0
                        or node.location.file is None and self.verbosity > 1):
                    debug = [
                        '  ' * self._depth,
                        node.kind,
                        '(type:%s | result type:%s)' % (node.type.kind, node.result_type.kind),
                        node.spelling,
                        node.location.file,
                    ]
                    if self.verbosity > 1:
                        debug.extend([
                            '[line %s:%s%s-%s]' % (
                                node.extent.start.line, node.extent.start.column,
                                ('line %s:' % node.extent.end.line)
                                    if node.extent.start.line != node.extent.end.line
                                    else '',
                                node.extent.end.column),
                        ])
                    if self.verbosity > 2:
                        debug.extend([
                            [t.spelling for t in node.get_tokens()]
                        ])
                    print(*debug)

                handler = getattr(self, 'handle_%s' % node.kind.name.lower())

                # If this node corresponds to a macro expansion,
                # move to macro expansion mode.
                if tokens is None:
                    try:
                        tokens = self.instantiated_macros[
                            (node.location.file and node.location.file.name, node.location.line, node.location.column)
                        ][:]
                    except KeyError:
                        pass

            except AttributeError:
                print(
                    "Ignoring node of type %s (%s)" % (
                        node.kind,
                        ' '.join(
                            t.spelling for t in node.get_tokens())
                        ),
                    file=sys.stderr
                )
                handler = None
        else:
            if '/usr/include/c++/v1' not in node.location.file.name:
                if node.location.file.name not in self.ignored_files:

                    if self.verbosity > 0:
                        print("Ignoring node in file %s" % node.location.file)
                    self.ignored_files.add(node.location.file.name)
            handler = None

        if handler:
            self._depth += 1
            result = handler(node, context, tokens)
            self._depth -= 1

            # Some definitions might be part of an inline typdef.
            # Keep a track of the last type defined, just in case
            # it needs to be referenced as part of a typedef.
            if node.kind.name.lower() in (
                        'struct_decl',
                        'union_decl',
                    ):
                self.last_decl = result
            else:
                self.last_decl = None

            return result

    def handle_unexposed_decl(self, node, context, tokens):
        # Ignore unexposed declarations (e.g., friend qualifiers)
        pass

    def handle_struct_decl(self, node, context, tokens):
        struct = Struct(context, node.spelling)
        for child in node.get_children():
            decl = self.handle(child, struct, tokens)
            if decl:
                decl.add_to_context(struct)
        return struct

    def handle_union_decl(self, node, context, tokens):
        union = Union(context, node.spelling)
        for child in node.get_children():
            decl = self.handle(child, union, tokens)
            if decl:
                decl.add_to_context(union)
        return union

    def handle_class_decl(self, node, context, tokens):
        klass = Class(context, node.spelling)
        for child in node.get_children():
            decl = self.handle(child, klass, tokens)
            if decl:
                decl.add_to_context(klass)
        return klass

    def handle_enum_decl(self, node, context, tokens):
        enum = Enumeration(context, node.spelling)
        for child in node.get_children():
            enum.add_enumerator(self.handle(child, enum, tokens))
        return enum

    def handle_field_decl(self, node, context, tokens):
        try:
            children = node.get_children()
            child = next(children)
            if child.kind == CursorKind.TYPE_REF:
                value = None
            else:
                value = self.handle(child, context, tokens)
            attr = Attribute(context, node.spelling, value)
        except StopIteration:
            attr = Attribute(context, node.spelling, None)

        # A field decl will have param children if the field
        # is a function pointer. However, we don't care about
        # the arguments; Python will duck type any call.

        return attr

    def handle_enum_constant_decl(self, node, enum, tokens):
        return EnumValue(node.spelling, node.enum_value)

    def handle_function_decl(self, node, context, tokens):
        function = Function(context, node.spelling)

        children = node.get_children()

        # If the return type is class, struct etc, then the first child will
        # be a TYPE_REF describing the return type; that node can be skipped.
        # A POINTER might be a pointer to a primitive type, in which case
        # there won't be a TYPE_REF node.
        if node.result_type.kind in (
                    TypeKind.RECORD,
                    TypeKind.ENUM,
                ):
            child = next(children)
            while child.kind == CursorKind.NAMESPACE_REF:
                child = next(children)

        elif node.result_type.kind in (
                    TypeKind.POINTER,
                    TypeKind.LVALUEREFERENCE,
                ):
            try:
                # Look up the pointee; if it's a defined type,
                # there will be a typedef node.
                context[node.result_type.get_pointee().spelling]
                child = next(children)
                while child.kind == CursorKind.NAMESPACE_REF:
                    child = next(children)
            except KeyError:
                pass

        for child in children:
            decl = self.handle(child, function, tokens)
            if decl:
                decl.add_to_context(function)
        return function

    def handle_var_decl(self, node, context, tokens):
        try:
            children = node.get_children()

            # print("VAR DECL")
            child = next(children)
            # print("FIRST CHILD", child.kind)

            # If the variable type is class, struct etc, then the first
            # children will be a series of TYPE_REFs describing the path to
            # the return type; those nodes can be skipped. A POINTER or
            # LVALUEREFERENCE might be a pointer to a primitive type, in which
            # case there won't be a TYPE_REF node. If a namespace is involved,
            # multiple NAMESPACE nodes will occur first.
            if node.type.kind in (
                        TypeKind.RECORD,
                        TypeKind.ENUM,
                    ):
                while child.kind == CursorKind.NAMESPACE_REF:
                    child = next(children)
                    # print("NS CHILD", child.kind)
                while child.kind == CursorKind.TYPE_REF:
                    child = next(children)
                    # print("TYPE CHILD", child.kind)

            elif node.type.kind in (
                        TypeKind.POINTER,
                        TypeKind.LVALUEREFERENCE,
                    ):
                try:
                    while child.kind == CursorKind.NAMESPACE_REF:
                        child = next(children)
                        # print("NS CHILD", child.kind)
                    # Look up the pointee; if it's a defined type,
                    # there will be a typedef node.
                    context[node.type.get_pointee().spelling]
                    # Otherwise - consume the type references
                    while child.kind == CursorKind.TYPE_REF:
                        child = next(children)
                        # print("POINTER/REF CHILD", child.kind)
                except KeyError:
                    pass
            # print("FINAL CHILD", child.kind)

            value = self.handle(child, context, tokens)
            # Array definitions put the array size first.
            # If there is a child, discard the value and
            # replace it with the list declaration.
            try:
                value = self.handle(next(children), context, tokens)
            except StopIteration:
                pass

            return Variable(context, node.spelling, value)
        except StopIteration:
            return None
            # Alternatively; explicitly set to None
            # return Variable(context, node.spelling)

    def handle_parm_decl(self, node, function, tokens):
        try:
            children = node.get_children()

            # If the parameter type is class, struct etc, then the first child
            # will be a TYPE_REF describing the return type; that node can be
            # skipped. A POINTER might be a pointer to a primitive type, in
            # which case there won't be a TYPE_REF node.
            if node.type.kind in (
                        TypeKind.RECORD,
                        TypeKind.ENUM,
                    ):
                child = next(children)
                while child.kind == CursorKind.NAMESPACE_REF:
                    child = next(children)

            elif node.type.kind in (
                        TypeKind.POINTER,
                        TypeKind.LVALUEREFERENCE,
                    ):
                try:
                    # Look up the pointee; if it's a defined type,
                    # there will be a typedef node.
                    function[node.type.get_pointee().spelling]
                    child = next(children)
                    while child.kind == CursorKind.NAMESPACE_REF:
                        child = next(children)
                except KeyError:
                    pass

            # If there is a child, it is the default value of the parameter.
            value = self.handle(next(children), function, tokens)
        except StopIteration:
            value = UNDEFINED

        param = Parameter(function, node.spelling, node.type.spelling, value)

        try:
            value = self.handle(next(children), function, tokens)
            raise Exception("Can't handle multiple children on parameter")
        except StopIteration:
            pass

        return param

    def handle_typedef_decl(self, node, context, tokens):
        if self.last_decl is None:
            c_type_name = ' '.join([t.spelling for t in node.get_tokens()][1:-2])
            return Variable(context, node.spelling, PrimitiveTypeReference(c_type_name))
        elif self.last_decl.name:
            return Variable(context, node.spelling, TypeReference(self.last_decl.name, node))
        else:
            self.last_decl.name = node.spelling

    def handle_cxx_method(self, node, context, tokens):
        # If this is an inline method, the context will be the
        # enclosing class, and the inline declaration will double as the
        # prototype.
        #
        # If it isn't inline, the context will be a module, and the
        # prototype will be separate. In this case, the method will
        # be found twice - once as the prototype, and once as the
        # definition.  Parameters are handled as part of the prototype;
        # this handle method only returns a new node when it finds the
        # prototype. When the body method is encountered, it finds the
        # prototype method (which will be the TYPE_REF in the first
        # child node), and adds the body definition.
        if isinstance(context, (Class, Struct, Union)):
            method = Method(context, node.spelling, node.is_pure_virtual_method(), node.is_static_method())
            is_prototype = True
        else:
            method = None
            is_prototype = False

        children = node.get_children()

        # If the return type is class, struct etc, then the first child will
        # be a TYPE_REF describing the return type; that node can be skipped.
        # A POINTER might be a pointer to a primitive type, in which case
        # there won't be a TYPE_REF node.
        if node.result_type.kind in (
                    TypeKind.RECORD,
                    TypeKind.ENUM,
                ):
            child = next(children)
            while child.kind == CursorKind.NAMESPACE_REF:
                child = next(children)

        elif node.result_type.kind in (
                    TypeKind.POINTER,
                    TypeKind.LVALUEREFERENCE,
                ):
            try:
                # Look up the pointee; if it's a defined type,
                # there will be a typedef node.
                context[node.result_type.get_pointee().spelling]
                child = next(children)
                while child.kind == CursorKind.NAMESPACE_REF:
                    child = next(children)
            except KeyError:
                pass

        for child in children:
            decl = self.handle(child, method, tokens)
            if method is None:
                # First node will be a TypeRef for the class.
                # Use this to get the method.
                method = context[decl.ref].methods[node.spelling]
            elif decl:
                if is_prototype or child.kind != CursorKind.PARM_DECL:
                    decl.add_to_context(method)

        # Only add a new node for the prototype.
        if is_prototype:
            return method

    def handle_namespace(self, node, module, tokens):
        # If the namespace already exists, add to it.
        try:
            submodule = module.submodules[node.spelling]
        except KeyError:
            submodule = Module(node.spelling, parent=module)

        for child in node.get_children():
            decl = self.handle(child, submodule, tokens)
            if decl:
                decl.add_to_context(submodule)
        return submodule

    # def handle_linkage_spec(self, node, context, tokens):

    def handle_constructor(self, node, context, tokens):
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
        #
        # This is done in two passes: the first pass finds the parameters,
        # and uses them to find/create the constructor; the second
        # adds statements.
        is_prototype = isinstance(context, Class)
        if is_prototype:
            constructor = Constructor(context)

            for child in node.get_children():
                if child.kind == CursorKind.PARM_DECL:
                    decl = self.handle(child, constructor, tokens)
                    constructor.add_parameter(decl)

            children = node.get_children()
        else:
            parameters = []
            for child in node.get_children():
                if child.kind == CursorKind.PARM_DECL:
                    decl = self.handle(child, context, tokens)
                    parameters.append(decl)

            children = node.get_children()

            # First node will be a TypeRef for the class.
            # Use this to get the constructor
            child = next(children)
            decl = self.handle(child, context, tokens)
            signature = tuple(p.ctype for p in parameters)
            try:
                constructor = context[decl.ref].constructors[signature]
            except KeyError:
                raise Exception("No match for constructor %s; options are %s" % (
                    signature, context[decl.ref].constructors.keys())
                )

        member_ref = None
        for child in children:
            decl = self.handle(child, constructor, tokens)
            if decl:
                if child.kind == CursorKind.COMPOUND_STMT:
                    constructor.add_statement(decl)
                elif child.kind == CursorKind.MEMBER_REF:
                    if member_ref is not None:
                        raise Exception("Unexpected member reference")
                    member_ref = decl
                elif member_ref is not None:
                    constructor.add_statement(
                        BinaryOperation(member_ref, '=', decl)
                    )
                    # Reset the member ref.
                    member_ref = None
                elif child.kind not in (CursorKind.PARM_DECL, CursorKind.TYPE_REF):
                    # Parm decls have
                    raise Exception("Don't know how to handle %s in constructor." % child.kind)

        # Only add a new node for the prototype.
        if is_prototype:
            return constructor

    def handle_destructor(self, node, context, tokens):
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
            decl = self.handle(child, destructor, tokens)
            if destructor is None:
                # First node will be a TypeRef for the class.
                # Use this to get the destructor
                destructor = context[decl.ref].destructor
            elif decl:
                if is_prototype or child.kind != CursorKind.PARM_DECL:
                    decl.add_to_context(destructor)

        # Only add a new node for the prototype.
        if is_prototype:
            return destructor

    # def handle_conversion_function(self, node, context, tokens):
    # def handle_template_type_parameter(self, node, context, tokens):
    # def handle_template_non_type_parameter(self, node, context, tokens):
    # def handle_template_template_parameter(self, node, context, tokens):
    # def handle_function_template(self, node, context, tokens):
    # def handle_class_template(self, node, context, tokens):
    # def handle_class_template_partial_specialization(self, node, context, tokens):
    # def handle_namespace_alias(self, node, context, tokens):
    # def handle_using_directive(self, node, context, tokens):
    # def handle_using_declaration(self, node, context, tokens):
    # def handle_type_alias_decl(self, node, context, tokens):

    def handle_cxx_access_spec_decl(self, node, context, tokens):
        # Ignore access specifiers; everything is public.
        pass

    def handle_type_ref(self, node, context, tokens):
        typename = node.spelling.split()[-1]
        return TypeReference(typename, node)

    def handle_cxx_base_specifier(self, node, context, tokens):
        context.superclass = node.spelling.split(' ')[1]

    # def handle_template_ref(self, node, context, tokens):

    def handle_namespace_ref(self, node, context, tokens):
        # Namespace references are handled by type scoping
        pass

    def handle_member_ref(self, node, context, tokens):
        try:
            children = node.get_children()
            child = next(children)
            ref = AttributeReference(self.handle(child, context, tokens), node.spelling)
        except StopIteration:
            # An implicit reference to `this`
            ref = AttributeReference(SelfReference(), node.spelling)

        try:
            next(children)
            raise Exception("Member reference has > 1 child node.")
        except StopIteration:
            pass
        return ref

    # def handle_label_ref(self, node, context, tokens):
    # def handle_overloaded_decl_ref(self, node, context, tokens):
    # def handle_variable_ref(self, node, context, tokens):
    # def handle_invalid_file(self, node, context, tokens):
    # def handle_no_decl_found(self, node, context, tokens):
    # def handle_not_implemented(self, node, context, tokens):
    # def handle_invalid_code(self, node, context, tokens):

    def handle_unexposed_expr(self, node, statement, tokens):
        # Ignore unexposed nodes; pass whatever is the first
        # (and should be only) child unaltered.
        try:
            children = node.get_children()
            expr = self.handle(next(children), statement, tokens)
        except StopIteration:
            # If an unexposed node has no children, it's a
            # default argument for a function. It can be ignored.
            return None

        try:
            next(children)
            raise Exception("Unexposed expression has > 1 children.")
        except StopIteration:
            pass

        return expr

    def handle_decl_ref_expr(self, node, statement, tokens):
        return VariableReference(node.spelling, node)

    def handle_member_ref_expr(self, node, context, tokens):
        try:
            children = node.get_children()
            first_child = next(children)
            ref = AttributeReference(self.handle(first_child, context, tokens), node.spelling)
        except StopIteration:
            # An implicit reference to `this`
            ref = AttributeReference(SelfReference(), node.spelling)

        try:
            next(children)
            raise Exception("Member reference expression has > 1 children.")
        except StopIteration:
            pass

        return ref

    def handle_call_expr(self, node, context, tokens):
        try:
            children = node.get_children()
            first_child = self.handle(next(children), context, tokens)

            if (isinstance(first_child, VariableReference) and (
                    first_child.node.type.kind == TypeKind.FUNCTIONPROTO
                    )) or isinstance(first_child, AttributeReference):

                fn = Invoke(first_child)

                for child in children:
                    arg = self.handle(child, context, tokens)
                    if arg:
                        fn.add_argument(arg)

                return fn
            else:
                # Implicit cast or functional cast
                return first_child
        except StopIteration:
            return Invoke(node.spelling)

    # def handle_block_expr(self, node, context, tokens):

    def handle_integer_literal(self, node, context, tokens):
        try:
            if tokens:
                content = tokens[0]
                tokens[0] = CONSUMED
            else:
                content = next(node.get_tokens()).spelling
        except StopIteration:
            # No tokens on the node;
            content = self.instantiated_macros[
                (node.location.file.name, node.location.line, node.location.column)
            ][0]

        return Literal(content)

    def handle_floating_literal(self, node, context, tokens):
        try:
            if tokens:
                content = tokens[0]
                tokens[0] = CONSUMED
            else:
                content = next(node.get_tokens()).spelling
        except StopIteration:
            content = self.instantiated_macros[
                (node.location.file.name, node.location.line, node.location.column)
            ][0]

        return Literal(content)

    # def handle_imaginary_literal(self, node, context, tokens):

    def handle_string_literal(self, node, context, tokens):
        try:
            if tokens:
                content = tokens[0]
                tokens[0] = CONSUMED
            else:
                content = next(node.get_tokens()).spelling
        except StopIteration:
            content = self.instantiated_macros[
                (node.location.file.name, node.location.line, node.location.column)
            ][0]

        return Literal(content)

    def handle_character_literal(self, node, context, tokens):
        try:
            if tokens:
                content = tokens[0]
                tokens[0] = CONSUMED
            else:
                content = next(node.get_tokens()).spelling
        except StopIteration:
            content = self.instantiated_macros[
                (node.location.file.name, node.location.line, node.location.column)
            ][0]

        return Literal(content)

    def handle_paren_expr(self, node, context, tokens):
        try:
            children = node.get_children()
            if tokens:
                # first and last tokens will be parentheses.
                tokens[0] = CONSUMED
                tokens[-1] = CONSUMED
                subtokens = tokens[1:-1]
            else:
                subtokens = None
            parens = Parentheses(self.handle(next(children), context, subtokens))
        except StopIteration:
            raise Exception("Parentheses must contain an expression.")

        try:
            next(children)
            raise Exception("Parentheses can only contain one expression.")
        except StopIteration:
            pass

        return parens

    def handle_unary_operator(self, node, context, tokens):
        try:
            children = node.get_children()
            child = next(children)

            if tokens:
                operand = tokens[0]
                tokens[0] = CONSUMED
                subtokens = tokens[1:]
            else:
                operand = list(node.get_tokens())[0].spelling
                subtokens = None

            # Dereferencing operator is a pass through.
            # All others must be processed as defined.
            if operand == '*':
                unaryop = self.handle(child, context, subtokens)
            else:
                op = operand
                value = self.handle(child, context, subtokens)
                unaryop = UnaryOperation(op, value)

        except StopIteration:
            raise Exception("Unary expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Unary expression has > 1 child node.")
        except StopIteration:
            pass

        return unaryop

    def handle_array_subscript_expr(self, node, context, tokens):
        try:
            children = node.get_children()

            subject = self.handle(next(children), context, tokens)
            index = self.handle(next(children), context, tokens)
            value = ArraySubscript(subject, index)
        except StopIteration:
            raise Exception("Array subscript requires 2 child nodes.")

        try:
            next(children)
            raise Exception("Array subscript has > 2 child nodes.")
        except StopIteration:
            pass

        return value

    def handle_binary_operator(self, node, context, tokens):
        try:
            children = node.get_children()

            lnode = next(children)
            lvalue = self.handle(lnode, context, tokens)

            if tokens:
                # Strip any consumed tokens
                tokens = [t for t in tokens if t is not CONSUMED]
                op = tokens[0]
                # Subtokens for rvalue will start after op.
                subtokens = tokens[1:]
            else:
                # Operator is the first token after the lnode's tokens.
                ltokens = len(list(lnode.get_tokens()))
                op = list(node.get_tokens())[ltokens - 1].spelling
                subtokens = None

            rnode = next(children)
            rvalue = self.handle(rnode, context, subtokens)
            binop = BinaryOperation(lvalue, op, rvalue)
        except StopIteration:
            raise Exception("Binary operator requires 2 child nodes.")

        try:
            next(children)
            raise Exception("Binary operator has > 2 child nodes.")
        except StopIteration:
            pass

        return binop

    def handle_compound_assignment_operator(self, node, context, tokens):
        try:
            children = node.get_children()

            lnode = next(children)
            lvalue = self.handle(lnode, context, tokens)

            if tokens:
                # Strip any consumed tokens
                tokens = [t for t in tokens if t is not CONSUMED]
                op = tokens[0]
                # Subtokens for rvalue will start after op.
                subtokens = tokens[1:]
            else:
                # Operator is the first token after the lnode's tokens.
                ltokens = len(list(lnode.get_tokens()))
                op = list(node.get_tokens())[ltokens - 1].spelling
                subtokens = None

            rnode = next(children)
            rvalue = self.handle(rnode, context, subtokens)
            binop = BinaryOperation(lvalue, op, rvalue)
        except StopIteration:
            raise Exception("Binary operator requires 2 child nodes.")

        try:
            next(children)
            raise Exception("Binary operator has > 2 child nodes.")
        except StopIteration:
            pass

        return binop

    def handle_conditional_operator(self, node, context, tokens):
        try:
            children = node.get_children()

            condition = self.handle(next(children), context, tokens)
            true_value = self.handle(next(children), context, tokens)
            false_value = self.handle(next(children), context, tokens)

            condop = ConditionalOperation(condition, true_value, false_value)
        except StopIteration:
            raise Exception("Conditional operator requires 3 child nodes.")

        try:
            next(children)
            raise Exception("Conditional operator has > 3 child nodes.")
        except StopIteration:
            pass

        return condop

    def handle_cstyle_cast_expr(self, node, context, tokens):
        try:
            children = node.get_children()
            child = next(children)

            # Consume any namespace or type nodes; they won't be
            # used for casting.
            while child.kind in (CursorKind.NAMESPACE_REF, CursorKind.TYPE_REF):
                child = next(children)

            cast = Cast(node.type.kind, self.handle(child, context, tokens))
        except StopIteration:
            raise Exception("Cast expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Cast expression has > 1 child node.")
        except StopIteration:
            pass

        return cast

    def handle_init_list_expr(self, node, context, tokens):
        children = node.get_children()

        value = ListLiteral()
        for child in children:
            value.append(self.handle(child, context, tokens))

        return value

    # def handle_addr_label_expr(self, node, context, tokens):
    # def handle_stmtexpr(self, node, context, tokens):
    # def handle_generic_selection_expr(self, node, context, tokens):
    # def handle_gnu_null_expr(self, node, context, tokens):

    def handle_cxx_static_cast_expr(self, node, context, tokens):
        try:
            children = node.get_children()
            child = next(children)

            # Consume any namespace or type nodes; they won't be
            # used for casting.
            while child.kind in (CursorKind.NAMESPACE_REF, CursorKind.TYPE_REF):
                child = next(children)

            cast = Cast(node.type.kind, self.handle(child, context, tokens))
        except StopIteration:
            raise Exception("Static cast expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Static cast expression has > 1 child node.")
        except StopIteration:
            pass

        return cast

    def handle_cxx_dynamic_cast_expr(self, node, context, tokens):
        try:
            children = node.get_children()
            child = next(children)

            # Consume any namespace or type nodes; they won't be
            # used for casting.
            while child.kind in (CursorKind.NAMESPACE_REF, CursorKind.TYPE_REF):
                child = next(children)

            cast = Cast(node.type.kind, self.handle(child, context, tokens))
        except StopIteration:
            raise Exception("Cast expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Cast expression has > 1 child node.")
        except StopIteration:
            pass

        return cast

    def handle_cxx_reinterpret_cast_expr(self, node, context, tokens):
        try:
            children = node.get_children()
            child = next(children)

            # Consume any namespace or type nodes; they won't be
            # used for casting.
            while child.kind in (CursorKind.NAMESPACE_REF, CursorKind.TYPE_REF):
                child = next(children)

            cast = Cast(node.type.kind, self.handle(child, context, tokens))
        except StopIteration:
            raise Exception("Cast expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Cast expression has > 1 child node.")
        except StopIteration:
            pass

        return cast

    def handle_cxx_const_cast_expr(self, node, context, tokens):
        try:
            children = node.get_children()
            child = next(children)

            # Consume any namespace or type nodes; they won't be
            # used for casting.
            while child.kind in (CursorKind.NAMESPACE_REF, CursorKind.TYPE_REF):
                child = next(children)

            cast = Cast(node.type.kind, self.handle(child, context, tokens))
        except StopIteration:
            raise Exception("Cast expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Cast expression has > 1 child node.")
        except StopIteration:
            pass

        return cast

    def handle_cxx_functional_cast_expr(self, node, context, tokens):
        try:
            children = node.get_children()

            if node.type.kind in (
                        TypeKind.CHAR_U,
                        TypeKind.UCHAR,
                        TypeKind.CHAR16,
                        TypeKind.CHAR32,
                        TypeKind.CHAR_S,
                        TypeKind.SCHAR,
                        TypeKind.WCHAR,
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
                        TypeKind.FLOAT,
                        TypeKind.DOUBLE,
                        TypeKind.LONGDOUBLE,
                    ):
                cast = Cast(node.type.kind, self.handle(next(children), context, tokens))
            else:
                cast = Invoke(self.handle(next(children), context, tokens))
                cast.add_argument(self.handle(next(children), context, tokens))
        except StopIteration:
            raise Exception("Functional cast requires 2 child nodes.")

        try:
            next(children)
            raise Exception("Functional cast has > 2 child nodes.")
        except StopIteration:
            pass

        return cast

    # def handle_cxx_typeid_expr(self, node, context, tokens):
    def handle_cxx_bool_literal_expr(self, node, context, tokens):
        try:
            if tokens:
                content = tokens[0]
                tokens[0] = CONSUMED
            else:
                content = next(node.get_tokens()).spelling
        except StopIteration:
            content = self.instantiated_macros[
                (node.location.file.name, node.location.line, node.location.column)
            ][0]

        return Literal('True' if content == 'true' else 'False')

    def handle_cxx_this_expr(self, node, context, tokens):
        return SelfReference()

    # def handle_cxx_throw_expr(self, node, context, tokens):
    def handle_cxx_new_expr(self, node, context, tokens):
        children = node.get_children()

        # If the class being instantiated is in a namespace, the
        # first children will be namespace nodes; these can be ignored.
        child = next(children)
        # print("FIRST CHILD", child.kind)
        while child.kind == CursorKind.NAMESPACE_REF:
            child = next(children)
            # print("NS CHILD", child.kind)

        # The next nodes will be typedefs, describing the path
        # to the class being instantiated. In most cases this will
        # be a single node; however, in the case of nested classes,
        # there will be multiple typedef nodes describing the access
        # path.
        while child.kind == CursorKind.TYPE_REF:
            type_ref = child
            child = next(children)
            # print("TYPE CHILD", child.kind)

        # print("FINAL CHILD", child.kind)
        new = New(self.handle(type_ref, context, tokens))

        for arg in child.get_children():
            new.add_argument(self.handle(arg, context, tokens))

        return new

    # def handle_cxx_delete_expr(self, node, context, tokens):
    # def handle_cxx_unary_expr(self, node, context, tokens):
    # def handle_pack_expansion_expr(self, node, context, tokens):
    # def handle_size_of_pack_expr(self, node, context, tokens):
    # def handle_lambda_expr(self, node, context, tokens):
    # def handle_unexposed_stmt(self, node, context, tokens):
    # def handle_label_stmt(self, node, context, tokens):

    def handle_compound_stmt(self, node, context, tokens):
        for child in node.get_children():
            statement = self.handle(child, context, tokens)
            if statement:
                context.add_statement(statement)

    def handle_if_stmt(self, node, context, tokens):
        children = node.get_children()
        condition = self.handle(next(children), context, tokens)
        if_statement = If(condition)

        self.handle(next(children), if_statement.if_true, tokens)
        try:
            # There are three possibilities here:
            # 1) No false condition (i.e., an if with no else). This
            #    is caught by the exception handler because there
            #    will be no child node.
            # 2) A bucket 'else' clause. The context passed to the
            #    handler will have the statements added to it.
            #    The handler will return None; the block passed
            #    as context is used as the if_false clause on the If.
            # 3) No false condition (i.e., an if with no else). The
            #    handler will process this as a "sub-if", and return
            #    the sub-if clause. This clause is used as the
            #    if_false clause on the If.
            if_false = Block()
            false_term = self.handle(next(children), if_false, tokens)
            if false_term:
                if_statement.if_false = false_term
            else:
                if_statement.if_false = if_false
        except StopIteration:
            pass

        try:
            next(children)
            raise Exception("Unexpected content in if statement")
        except StopIteration:
            pass

        return if_statement

    # def handle_switch_stmt(self, node, context, tokens):
    # def handle_case_stmt(self, node, context, tokens):
    # def handle_default_stmt(self, node, context, tokens):

    # def handle_while_stmt(self, node, context, tokens):
    # def handle_do_stmt(self, node, context, tokens):
    # def handle_for_stmt(self, node, context, tokens):
    # def handle_goto_stmt(self, node, context, tokens):
    # def handle_indirect_goto_stmt(self, node, context, tokens):
    # def handle_continue_stmt(self, node, context, tokens):
    # def handle_break_stmt(self, node, context, tokens):

    def handle_return_stmt(self, node, context, tokens):
        retval = Return()
        try:
            retval.value = self.handle(next(node.get_children()), context, tokens)
        except StopIteration:
            pass

        return retval

    # def handle_asm_stmt(self, node, context, tokens):
    # def handle_cxx_catch_stmt(self, node, context, tokens):
    # def handle_cxx_try_stmt(self, node, context, tokens):
    # def handle_cxx_for_range_stmt(self, node, context, tokens):
    # def handle_seh_try_stmt(self, node, context, tokens):
    # def handle_seh_except_stmt(self, node, context, tokens):
    # def handle_seh_finally_stmt(self, node, context, tokens):
    # def handle_ms_asm_stmt(self, node, context, tokens):
    # def handle_null_stmt(self, node, context, tokens):
    def handle_decl_stmt(self, node, context, tokens):
        try:
            children = node.get_children()
            statement = self.handle(next(children), context, tokens)
        except StopIteration:
            pass

        try:
            self.handle(next(children), context, tokens)
            raise Exception("Don't know how to handle multiple statements")
        except StopIteration:
            pass

        return statement

    def handle_translation_unit(self, node, tu, tokens):
        for child in node.get_children():
            decl = self.handle(child, tu, tokens)
            if decl:
                decl.add_to_context(tu)

    # def handle_unexposed_attr(self, node, context, tokens):
    # def handle_ib_action_attr(self, node, context, tokens):
    # def handle_ib_outlet_attr(self, node, context, tokens):
    # def handle_ib_outlet_collection_attr(self, node, context, tokens):
    # def handle_cxx_final_attr(self, node, context, tokens):

    def handle_cxx_override_attr(self, node, context, tokens):
        # No need to handle override declarations
        pass

    # def handle_annotate_attr(self, node, context, tokens):
    # def handle_asm_label_attr(self, node, context, tokens):
    # def handle_packed_attr(self, node, context, tokens):
    # def handle_pure_attr(self, node, context, tokens):
    # def handle_const_attr(self, node, context, tokens):
    # def handle_noduplicate_attr(self, node, context, tokens):
    # def handle_cudaconstant_attr(self, node, context, tokens):
    # def handle_cudadevice_attr(self, node, context, tokens):
    # def handle_cudaglobal_attr(self, node, context, tokens):
    # def handle_cudahost_attr(self, node, context, tokens):
    # def handle_cudashared_attr(self, node, context, tokens):
    # def handle_visibility_attr(self, node, context, tokens):
    # def handle_dllexport_attr(self, node, context, tokens):
    # def handle_dllimport_attr(self, node, context, tokens):
    # def handle_preprocessing_directive(self, node, context, tokens):

    def handle_macro_definition(self, node, context, tokens):
        tokens = node.get_tokens()
        key = next(tokens).spelling
        # The value needs a little extra filtering;
        # clang has a bug that includes stray tokens
        # int the token defintion for macros.
        value = list(t.spelling for t in tokens if t.location in node.extent)
        self.macros[key] = value

    def handle_macro_instantiation(self, node, context, tokens):
        self.instantiated_macros[
            (node.location.file.name, node.location.line, node.location.column)
        ] = self.macros.get(node.spelling, '')

    def handle_inclusion_directive(self, node, context, tokens):
        # Ignore inclusion directives
        pass

    # def handle_module_import_decl(self, node, context, tokens):
    # def handle_type_alias_template_decl(self, node, context, tokens):

    ############################################################
    # Objective-C methods
    # If an algorithm exists in Objective C, implementing these
    # methods will allow conversion of that code.
    ############################################################
    # def handle_objc_synthesize_decl(self, node, context, tokens):
    # def handle_objc_dynamic_decl(self, node, context, tokens):
    # def handle_objc_super_class_ref(self, node, context, tokens):
    # def handle_objc_protocol_ref(self, node, context, tokens):
    # def handle_objc_class_ref(self, node, context, tokens):
    # def handle_objc_message_expr(self, node, context, tokens):
    # def handle_objc_string_literal(self, node, context, tokens):
    # def handle_objc_encode_expr(self, node, context, tokens):
    # def handle_objc_selector_expr(self, node, context, tokens):
    # def handle_objc_protocol_expr(self, node, context, tokens):
    # def handle_objc_bridge_cast_expr(self, node, context, tokens):
    # def handle_obj_bool_literal_expr(self, node, context, tokens):
    # def handle_obj_self_expr(self, node, context, tokens):
    # def handle_objc_at_try_stmt(self, node, context, tokens):
    # def handle_objc_at_catch_stmt(self, node, context, tokens):
    # def handle_objc_at_finally_stmt(self, node, context, tokens):
    # def handle_objc_at_throw_stmt(self, node, context, tokens):
    # def handle_objc_at_synchronized_stmt(self, node, context, tokens):
    # def handle_objc_autorelease_pool_stmt(self, node, context, tokens):
    # def handle_objc_for_collection_stmt(self, node, context, tokens):
    # def handle_objc_interface_decl(self, node, context, tokens):
    # def handle_objc_category_decl(self, node, context, tokens):
    # def handle_objc_protocol_decl(self, node, context, tokens):
    # def handle_objc_property_decl(self, node, context, tokens):
    # def handle_objc_ivar_decl(self, node, context, tokens):
    # def handle_objc_instance_method_decl(self, node, context, tokens):
    # def handle_objc_class_method_decl(self, node, context, tokens):
    # def handle_objc_implementation_decl(self, node, context, tokens):
    # def handle_objc_category_impl_decl(self, node, context, tokens):


# A simpler version of Parser that just
# dumps the tree structure.
class CodeDumper(BaseParser):
    def __init__(self, verbosity):
        super(CodeDumper, self).__init__()
        self.verbosity = verbosity

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
        debug = [
            '    ' * depth,
            node.kind,
            '(type:%s | result type:%s)' % (node.type.kind, node.result_type.kind),
            node.spelling,
            node.location.file,
        ]
        if self.verbosity > 0:
            debug.append([t.spelling for t in node.get_tokens()])
        print(*debug)

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
        help='Preprocessor tokens to use',
        action='append',
        default=[]
    )

    opts.add_argument(
        '-v', '--verbosity',
        action='count',
        default=0
    )

    opts.add_argument(
        'filename',
        metavar='file.cpp',
        help='The file(s) to dump.',
        nargs="+"
    )

    args = opts.parse_args()

    dumper = CodeDumper(verbosity=args.verbosity)
    for filename in args.filename:
        dumper.parse(
            filename,
            flags=[
                '-I%s' % inc for inc in args.includes
            ] + [
                '-D%s' % define for define in args.defines
            ]
        )
