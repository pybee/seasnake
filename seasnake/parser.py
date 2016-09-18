###########################################################################
# Code Parser
#
# This uses the clang Python API to parse and traverse the AST for C++
# code, producing a data model.
###########################################################################
from __future__ import unicode_literals, print_function

import argparse
import os
import re
import sys

from clang.cindex import (
    CursorKind,
    Index,
    StorageClass,
    TranslationUnit,
    TypeKind,
    UnaryOperator
)

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

        self.namespace = self.root_module

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

    def parse(self, filenames, flags):
        abs_filenames = [os.path.abspath(f) for f in filenames]
        self.filenames.update(abs_filenames)

        for filename in abs_filenames:
            if os.path.splitext(filename)[1] != '.h':
                self.tu = self.index.parse(
                    filename,
                    args=flags,
                    options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
                )
                self.handle(self.tu.cursor, self.root_module)

    def parse_text(self, content, flags):
        for f, c in content:
            abs_filename = os.path.abspath(f)
            self.filenames.add(abs_filename)

            self.tu = self.index.parse(
                f,
                args=flags,
                unsaved_files=[(f, c)],
                options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
            )
            self.handle(self.tu.cursor, self.root_module)

    def localize_namespace(self, namespace):
        """Strip any namespace parts that are implied by the current namespace.

        This takes into account the current namespace, and any `using`
        declarations that are currently in effect.
        """
        namespace = self.root_module.full_name + '::' + namespace.strip('::')

        # Strip the current namespace or using prefix
        # if there is an overlap.
        if namespace.startswith(self.namespace.full_name):
            namespace = namespace[len(self.namespace.full_name) + 2:]
        #else:
            #for using_namespace in self.using:
            #    # TODO: handle USING statements.
            #    pass

        # If there's still a namespace, add a separator
        # so it can prefixed onto the name to be used.
        if namespace:
            namespace += "::"

        return namespace
    
    def lookup(self, children, context):
        """Utility function to lookup a namespaced object"""
        child = next(children)
        names = []
        try:
            while child.kind == CursorKind.NAMESPACE_REF:
                names.append(child.spelling)
                child = next(children)
        except StopIteration:
            child = None
        
        if names:
            context = self.root_module['::'.join(names)]
            
        return child, context
        

    def handle(self, node, context=None):
        if (node.location.file is None
                or os.path.abspath(node.location.file.name) in self.filenames):
            try:
                if ((node.location.file or node.kind == CursorKind.TRANSLATION_UNIT) and self.verbosity > 0
                        or node.location.file is None and self.verbosity > 1):
                    debug = [
                        '  ' * self._depth,
                        context,
                        node.kind,
                        '(type:%s | result type:%s)' % (node.type.kind, node.result_type.kind),
                        node.spelling,
                        node.location.file
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
            if node.location.file.name.startswith('/usr/include'):
                min_level = 2
            elif node.location.file.name.startswith('/usr/local'):
                min_level = 2
            else:
                min_level = 1

            if node.location.file.name not in self.ignored_files:
                if self.verbosity >= min_level:
                    print("Ignoring node in file %s" % node.location.file)
                self.ignored_files.add(node.location.file.name)
            handler = None

        if handler:
            self._depth += 1
            result = handler(node, context)
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

    def handle_unexposed_decl(self, node, context):
        # Ignore unexposed declarations (e.g., friend qualifiers)
        pass

    def handle_struct_decl(self, node, context):
        # If a struct is pre-declared, use the existing declaration,
        # rather than overwriting the old one.
        try:
            struct = context[node.spelling]
        except KeyError:
            struct = Struct(context, node.spelling)

        for child in node.get_children():
            decl = self.handle(child, struct)
            if decl:
                decl.add_to_context(struct)
        return struct

    def handle_union_decl(self, node, context):
        # If a union is pre-declared, use the existing declaration,
        # rather than overwriting the old one.
        try:
            union = context[node.spelling]
        except KeyError:
            union = Union(context, node.spelling)

        for child in node.get_children():
            decl = self.handle(child, union)
            if decl:
                decl.add_to_context(union)
        return union

    def handle_class_decl(self, node, context):
        # If a class is pre-declared, use the existing declaration,
        # rather than overwriting the old one.
        try:
            klass = context[node.spelling]
        except KeyError:
            klass = Class(context, node.spelling)

        # To avoid forward declaration issues, run two passes
        # over the class.
        #
        # The first pass picks up any names that might be referred
        # to by inline methods (enums, fields, etc)
        for child in node.get_children():
            if child.type.kind != TypeKind.FUNCTIONPROTO:
                # Handle enums and fields first
                decl = self.handle(child, klass)
                if decl:
                    decl.add_to_context(klass)

        # The second pass parses the methods.
        for child in node.get_children():
            if child.type.kind == TypeKind.FUNCTIONPROTO:
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
            is_static = node.storage_class == StorageClass.STATIC

            children = node.get_children()
            child = next(children)
            if child.kind == CursorKind.TYPE_REF:
                value = None
            else:
                value = self.handle(child, context)

            # If the node is of type CONSTANTARRAY, then the field
            # is an array; set the value to a tuple of that size.
            # Otherwise, ignore the value; You need to be at C++11
            # to be using that feature, anyway.
            if node.type.kind == TypeKind.CONSTANTARRAY:
                value = Literal(text(tuple(None for i in range(0, int(value.value)))))
            else:
                value = None

            attr = Attribute(context, node.spelling, value=value, static=is_static)
        except StopIteration:
            attr = Attribute(context, node.spelling, value=None, static=is_static)

        # A field decl will have param children if the field
        # is a function pointer. However, we don't care about
        # the arguments; Python will duck type any call.

        return attr

    def handle_enum_constant_decl(self, node, context):
        return EnumValue(context, node.spelling, node.enum_value)

    def handle_function_decl(self, node, context):
        function = Function(context, node.spelling)
        try:
            # print("FUNCTION DECL")
            children = node.get_children()
            child = next(children)

            # If the node has any children, the first children will be the
            # return type and namespace for the function declaration. These
            # nodes can be ignored.
            # print("FIRST CHILD", child.kind)
            while child.kind == CursorKind.NAMESPACE_REF:
                child = next(children)
                # print("NS CHILD", child.kind)
            while child.kind == CursorKind.TYPE_REF:
                child = next(children)
                # print("TYPE REF CHILD", child.kind)

            # Subsequent nodes will be the parameters for the function.
            try:
                while True:
                    decl = self.handle(child, function)
                    if decl:
                        decl.add_to_context(function)
                    child = next(children)
            except StopIteration:
                pass

        except StopIteration:
            pass

        # Only return a node if we get function definition. The prototype
        # can be ignored.
        if function.statements is not None:
            return function

    def handle_var_decl(self, node, context):
        try:
            # print("VAR DECL")
            children = node.get_children()
            prev_child = None
            child = next(children)
            # print("FIRST CHILD", child.kind)

            # If there are children, the first children will define the
            # namespace and type for the variable being declared (or the context
            # for the variable in the case of an assignment). Ignore these
            # nodes, and go straight to the actual content.
            while child.kind == CursorKind.NAMESPACE_REF:
                prev_child = child
                child = next(children)
                # print("NS CHILD", child.kind, child.spelling)
            while child.kind == CursorKind.TYPE_REF:
                prev_child = child
                child = next(children)
                # print("TYPE REF CHILD", child.kind, child.spelling)

            # print("FINAL CHILD", child.kind, child.spelling)
            # print("NAMESPACE", namespace)
            value = self.handle(child, context)
            if prev_child and child.type.kind == TypeKind.RECORD and child.kind == CursorKind.INIT_LIST_EXPR:
                value = New(TypeReference(context[prev_child.type.spelling]))
                for arg in child.get_children():
                    value.add_argument(self.handle(arg, context))
            else:
                # Array definitions put the array size first.
                # If there is a child, discard the value and
                # replace it with the list declaration.
                try:
                    value = self.handle(next(children), context)
                except StopIteration:
                    pass

            # If the current context is a module, then we are either defining a
            # global variable, or setting a static constant. If the context is a
            # class/struct/union, we're defining a static attribute. The typedef
            # captured as the initial child nodes tells us the path to the variable
            # being set.
            if prev_child and isinstance(context, Module):
                full_namespace = prev_child.spelling.split()[-1]
                decl_context = context[full_namespace]
                # print("DECL CONTEXT", decl_context)
                namespace = self.localize_namespace(full_namespace)
            else:
                namespace = ''
                decl_context = context

            if isinstance(context, (Class, Struct, Union)):
                # print("ATTR DECL with value %s, %s, %s, %s" % (context, namespace, node.spelling, value))
                return Attribute(context, node.spelling, value=value, static=True)
            else:
                if isinstance(decl_context, (Class, Struct, Union)):
                    # print("ATTR ASSIGN with value %s, %s, %s, %s" % (context, namespace, node.spelling, value))
                    return BinaryOperation(
                        AttributeReference(TypeReference(decl_context), node.spelling),
                        '=', value
                    )
                else:
                    # print("VAR DECL with value %s, %s, %s, %s" % (context, namespace, node.spelling, value))
                    return Variable(decl_context, namespace + node.spelling, value)

        except StopIteration:
            # No initial value for the variable. If the context is a module,
            # class, struct or union (i.e., high level block structures)
            # it still needs to be declared; use a value of None.
            if isinstance(context, Module):
                # print("VAR DECL no value %s, %s" % (context, node.spelling))
                return Variable(context, node.spelling, value=None)
            elif isinstance(context, (Class, Struct, Union)):
                # print("ATTR DECL no value %s, %s" % (context, node.spelling))
                is_static = node.storage_class == StorageClass.STATIC
                return Attribute(context, node.spelling, value=None, static=is_static)
            else:
                # print("pre-decl no value %s, %s" % (context, node.spelling))
                return Variable(context, node.spelling, value=UNDEFINED)

    def handle_parm_decl(self, node, function):
        try:
            children = node.get_children()
            child = next(children)

            # If there are any children, this will be a parameter
            # with a default value. The children will be the reference
            # to the default value.
            # If the default value is a non-primitive type, there will
            # be NAMESPACE_REF and TYPE_REF nodes; all but the last one
            # can be ignored.

            # Any namespace nodes can be stripped
            while child.kind in [CursorKind.NAMESPACE_REF,
                                 CursorKind.TYPE_REF,
                                 CursorKind.TEMPLATE_REF]:
                child = next(children)

            # If there is a child, it is the default value of the parameter.
            value = self.handle(child, function)
        except StopIteration:
            value = UNDEFINED

        param = Parameter(function, node.spelling, node.type.spelling, value)

        try:
            value = self.handle(next(children), function)
            raise Exception("Can't handle multiple children on parameter")
        except StopIteration:
            pass

        return param

    def handle_typedef_decl(self, node, context):
        if self.last_decl is None:
            c_type_name = node.underlying_typedef_type.spelling
            try:
                type_ref = PrimitiveTypeReference({
                    'unsigned': 'int',
                    'unsigned byte': 'int',
                    'unsigned short': 'int',
                    'unsigned int': 'int',
                    'unsigned long': 'int',
                    'unsigned long long': 'int',
                    'signed': 'int',
                    'short': 'int',
                    'long': 'int',
                    'int': 'int',
                    'long long': 'int',
                    'double': 'float',
                    'float': 'float',
                }[c_type_name])
            except KeyError:
                # Remove any template instantiation from the type.
                type_name = re.sub('<.*>', '', c_type_name)
                type_ref = TypeReference(context[type_name])

            return Typedef(context, node.spelling, type_ref)
        elif self.last_decl.name:
            return Typedef(context, node.spelling, TypeReference(context[self.last_decl.name]))
        else:
            self.last_decl.name = node.spelling

    def handle_cxx_method(self, node, context):
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
            # print("IS PROTOTYPE")
        else:
            method = None
            # print("NOT PROTOTYPE")
            is_prototype = False

        children = node.get_children()
        try:
            prev_child = None
            child = next(children)

            # We can ignore override and final attributes on methods.
            while child.kind == CursorKind.CXX_OVERRIDE_ATTR:
                prev_child = child
                child = next(children)
            while child.kind == CursorKind.CXX_FINAL_ATTR:
                prev_child = child
                child = next(children)

            # Then comes the typedef for the return value.
            while child.kind in [CursorKind.NAMESPACE_REF,
                                 CursorKind.TYPE_REF,
                                 CursorKind.TEMPLATE_REF]:
                prev_child = child
                child = next(children)

            if method is None:
                ref = self.handle(prev_child, context)
                method = ref.type.methods[node.spelling]

            p = 0
            while True:
                # print("CHILD", child.kind, child.spelling)
                decl = self.handle(child, method)
                if decl:
                    if is_prototype or child.kind != CursorKind.PARM_DECL:
                        decl.add_to_context(method)

                    # Take the parameter names from the implementation version.
                    if not is_prototype and child.kind == CursorKind.PARM_DECL:
                        method.parameters[p].name = decl.name
                        p += 1

                child = next(children)
        except StopIteration:
            pass

        # Add a new node for the prototype. Definitions will
        # build on the pre-existing node.
        if is_prototype:
            return method

    def handle_namespace(self, node, module):
        # If the namespace already exists, add to it.
        anonymous_ns = not node.spelling
        if anonymous_ns:
            submodule = module
        else:
            try:
                submodule = module.submodules[node.spelling]
            except KeyError:
                submodule = Module(node.spelling, context=module)

        # Set the current namespace, and clone the current using list.
        self.namespace = submodule
        #using = self.using.copy()

        # Process the contents of the namespace
        for child in node.get_children():
            decl = self.handle(child, submodule)
            if decl:
                decl.add_to_context(submodule)

        # Restore the previously active namespace and using list.
        self.namespace = module
        #self.using = using

        if not anonymous_ns:
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
        try:
            children = node.get_children()
            is_prototype = isinstance(context, (Class, Struct))
            if is_prototype:
                constructor = Constructor(context)

                child = next(children)
                while child.kind == CursorKind.PARM_DECL:
                    decl = self.handle(child, constructor)
                    constructor.add_parameter(decl)
                    child = next(children)
            else:
                parameters = []
                prev_child = None
                child = next(children)
                while child.kind == CursorKind.TYPE_REF:
                    prev_child = child
                    child = next(children)

                while child.kind == CursorKind.PARM_DECL:
                    decl = self.handle(child, context)
                    parameters.append(decl)
                    child = next(children)

                signature = tuple(p.ctype for p in parameters)
                try:
                    ref = self.handle(prev_child, context)
                    constructor = ref.type.constructors[signature]
                    for cp, p in zip(constructor.parameters, parameters):
                        cp.name = p.name
                except KeyError:
                    raise Exception("No match for constructor %s; options are %s" % (
                        signature, ref.type.constructors.keys())
                    )

            member_ref = None
            while True:
                decl = self.handle(child, constructor)
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
                child = next(children)
        except StopIteration:
            pass

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
        try:
            children = node.get_children()
            is_prototype = isinstance(context, (Class, Struct))
            if is_prototype:
                destructor = Destructor(context)
                child = next(children)
            else:
                prev_child = None
                child = next(children)
                while child.kind == CursorKind.TYPE_REF:
                    prev_child = child
                    child = next(children)

                try:
                    ref = self.handle(prev_child, context)
                    destructor = ref.type.destructor
                except KeyError:
                    raise Exception("No destructor declared on class")

            while True:
                decl = self.handle(child, destructor)
                if decl:
                    decl.add_to_context(destructor)
                child = next(children)

        except StopIteration:
            pass

        # Only add a new node for the prototype.
        if is_prototype:
            return destructor

    # def handle_conversion_function(self, node, context):

    def handle_template_type_parameter(self, node, context):
        # Type paramteres can be ignored; templated types are duck typed
        pass

    # def handle_template_non_type_parameter(self, node, context):
    # def handle_template_template_parameter(self, node, context):
    def handle_function_template(self, node, context):
        # Treat a function template like any other function declaration.
        # Templated types will be duck typed.
        if isinstance(context, Class):
            return self.handle_cxx_method(node, context)
        else:
            return self.handle_function_decl(node, context)

    def handle_class_template(self, node, context):
        # Treat a class template like any other class declaration.
        # Templated types will be duck typed.
        return self.handle_class_decl(node, context)

    # def handle_class_template_partial_specialization(self, node, context):
    # def handle_namespace_alias(self, node, context):
    def handle_using_directive(self, node, context):
        child, ns_context = self.lookup(node.get_children(), context)
        if child is not None:
            # We've got a node that isn't a namespace
            raise Exception("Don't know how to handle node of type %s in using directive" % child.kind)
        
        context.related_contexts.add(ns_context)

    def handle_using_declaration(self, node, context):
        children = node.get_children()
        child, ns = self.lookup(children, context)
        context.add_using_decl(ns[child.spelling])
                
    # def handle_type_alias_decl(self, node, context):

    def handle_cxx_access_spec_decl(self, node, context):
        # Ignore access specifiers; everything is public.
        pass

    def handle_type_ref(self, node, context):
        typename = node.spelling.split()[-1]
        return TypeReference(context[typename])

    def handle_cxx_base_specifier(self, node, context):
        typename = node.spelling.split()[1]
        context.superclass = TypeReference(context[typename])

    def handle_template_ref(self, node, context):
        typename = node.spelling.split()[-1]
        return TypeReference(context[typename])

    def handle_namespace_ref(self, node, context):
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
            return None

        try:
            next(children)
            raise Exception("Unexposed expression has > 1 children.")
        except StopIteration:
            pass

        return expr

    def handle_decl_ref_expr(self, node, context):
        children = node.get_children()
        namespace = ''
        try:
            child = next(children)
            while child.kind == CursorKind.NAMESPACE_REF:
                namespace += child.spelling + '::'
                child = next(children)
            while child.kind == CursorKind.TYPE_REF:
                namespace = child.spelling.split()[-1] + '::'
                child = next(children)
        except StopIteration:
            pass

        try:
            child = next(children)
            raise Exception("Unexpected %s child node in declaration" % child.type)
        except StopIteration:
            pass

        var = context[namespace + node.spelling]
        if isinstance(var, EnumValue):
            return var
        else:
            return VariableReference(context[namespace + node.spelling], node)

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
            namespace = ""
            children = node.get_children()
            child = next(children)
            
            while child.kind == CursorKind.NAMESPACE_REF:
                namespace += child.spelling + '::'
                child = next(children)
            prev_child = child
            while child.kind == CursorKind.TYPE_REF:
                child = next(children)
                if prev_child.type.kind == TypeKind.RECORD:
                    # Class typerefs in a call include their own
                    # namespace definition.
                    namespace = prev_child.spelling.split()[-1] + '::'
                else:
                    namespace += prev_child.spelling + '::'
                prev_child = child

            first_child = self.handle(child, context)
            if ((isinstance(first_child, VariableReference)
                        and first_child.node.type.kind == TypeKind.FUNCTIONPROTO)
                    or isinstance(first_child, AttributeReference)):
                fn = Invoke(first_child)

                for child in children:
                    arg = self.handle(child, context)
                    if arg:
                        fn.add_argument(arg.clean_argument())

                return fn
            else:
                # Implicit cast, functional cast, or
                # constructor with no args
                return first_child
        except StopIteration:
            return Invoke(TypeReference(context[namespace + node.spelling]))

    # def handle_block_expr(self, node, context):

    def handle_integer_literal(self, node, context):
        # In order to preserve source formatting, we need to do some
        # special handling. The literal from the AST will be processed
        # into a decimal integer, losing all formatting. However,
        # the token will be unreliable as a way of getting the token.
        # So - get both; if they're numerically equal, use the token
        # because it will have preserved formatting. If they aren't
        # equal, the token is probably wrong; use the literal.
        try:
            literal_value = node.literal
            token_value = next(node.get_tokens()).spelling

            try:
                if int(token_value) == int(literal_value):
                    value = token_value
                else:
                    raise ValueError()
            except ValueError:
                try:
                    if int(token_value, 16) == int(literal_value):
                        value = token_value
                    else:
                        try:
                            # Try octals
                            if int(token_value, 8) == int(literal_value):
                                value = token_value
                            else:
                                raise ValueError()
                        except ValueError:
                            raise ValueError()
                except ValueError:
                    value = literal_value
        except StopIteration:
            # No tokens
            value = literal_value

        return Literal(value)

    def handle_floating_literal(self, node, context):
        try:
            literal_value = node.literal
            token_value = next(node.get_tokens()).spelling
            if float(token_value) == float(literal_value):
                value = token_value
            else:
                value = literal_value
        except (StopIteration, ValueError):
            # No tokens
            value = literal_value

        return Literal(value)

    # def handle_imaginary_literal(self, node, context):

    def handle_string_literal(self, node, context):
        return Literal(node.literal)

    def handle_character_literal(self, node, context):
        return Literal(node.literal)

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

            op = node.unary_operator

            # Dereferencing operator is a pass through.
            # All others must be processed as defined.
            if op == UnaryOperator.DEREF:
                unaryop = self.handle(child, context)
            else:
                value = self.handle(child, context)
                unaryop = UnaryOperation(node.operator, value)

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

            op = node.operator

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

    def handle_compound_assignment_operator(self, node, context):
        try:
            children = node.get_children()

            lnode = next(children)
            lvalue = self.handle(lnode, context)

            op = node.operator

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

    def handle_conditional_operator(self, node, context):
        try:
            children = node.get_children()

            condition = self.handle(next(children), context)
            true_value = self.handle(next(children), context)
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

            # Consume any namespace or type nodes; they won't be
            # used for casting.
            while child.kind in (CursorKind.NAMESPACE_REF, CursorKind.TYPE_REF):
                child = next(children)

            cast = Cast(node.type.kind, self.handle(child, context))
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

    def handle_cxx_null_ptr_literal_expr(self, node, context):
        return Literal(None)

    def handle_gnu_null_expr(self, node, context):
        return Literal(None)

    def handle_cxx_static_cast_expr(self, node, context):
        try:
            children = node.get_children()
            child = next(children)

            # Consume any namespace or type nodes; they won't be
            # used for casting.
            while child.kind in (CursorKind.NAMESPACE_REF, CursorKind.TYPE_REF):
                child = next(children)

            cast = Cast(node.type.kind, self.handle(child, context))
        except StopIteration:
            raise Exception("Static cast expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Static cast expression has > 1 child node.")
        except StopIteration:
            pass

        return cast

    def handle_cxx_dynamic_cast_expr(self, node, context):
        try:
            children = node.get_children()
            child = next(children)

            # Consume any namespace or type nodes; they won't be
            # used for casting.
            while child.kind in (CursorKind.NAMESPACE_REF, CursorKind.TYPE_REF):
                child = next(children)

            cast = Cast(node.type.kind, self.handle(child, context))
        except StopIteration:
            raise Exception("Cast expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Cast expression has > 1 child node.")
        except StopIteration:
            pass

        return cast

    def handle_cxx_reinterpret_cast_expr(self, node, context):
        try:
            children = node.get_children()
            child = next(children)

            # Consume any namespace or type nodes; they won't be
            # used for casting.
            while child.kind in (CursorKind.NAMESPACE_REF, CursorKind.TYPE_REF):
                child = next(children)

            cast = Cast(node.type.kind, self.handle(child, context))
        except StopIteration:
            raise Exception("Cast expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Cast expression has > 1 child node.")
        except StopIteration:
            pass

        return cast

    def handle_cxx_const_cast_expr(self, node, context):
        try:
            children = node.get_children()
            child = next(children)

            # Consume any namespace or type nodes; they won't be
            # used for casting.
            while child.kind in (CursorKind.NAMESPACE_REF, CursorKind.TYPE_REF):
                child = next(children)

            cast = Cast(node.type.kind, self.handle(child, context))
        except StopIteration:
            raise Exception("Cast expression requires 1 child node.")

        try:
            next(children)
            raise Exception("Cast expression has > 1 child node.")
        except StopIteration:
            pass

        return cast

    def handle_cxx_functional_cast_expr(self, node, context):
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
                cast = Cast(node.type.kind, self.handle(next(children), context))
            else:
                cast = Invoke(self.handle(next(children), context))
                cast.add_argument(self.handle(next(children), context))
        except StopIteration:
            raise Exception("Functional cast requires 2 child nodes.")

        try:
            next(children)
            raise Exception("Functional cast has > 2 child nodes.")
        except StopIteration:
            pass

        return cast

    # def handle_cxx_typeid_expr(self, node, context):
    def handle_cxx_bool_literal_expr(self, node, context):
        content = node.literal
        return Literal('True' if content == 'true' else 'False')

    def handle_cxx_this_expr(self, node, context):
        return SelfReference()

    # def handle_cxx_throw_expr(self, node, context):
    def handle_cxx_new_expr(self, node, context):
        children = node.get_children()

        # If the class being instantiated is in a namespace, the
        # first children will be namespace nodes; these can be ignored.
        child = next(children)
        # print("FIRST CHILD", child.kind)
        while child.kind == CursorKind.NAMESPACE_REF:
            child = next(children)
            # print("NS CHILD", child.kind)

        # The next nodes will be typedefs or a template reference describing
        # the path to the class being instantiated. In most cases this will be
        # a single node; however, in the case of nested classes, there will be
        # multiple typedef nodes describing the access path.
        while child.kind in (CursorKind.TYPE_REF, CursorKind.TEMPLATE_REF):
            type_ref = child
            child = next(children)
            # print("TYPE CHILD", child.kind)

        # print("FINAL CHILD", child.kind)
        new = New(self.handle(type_ref, context))

        for arg in child.get_children():
            new.add_argument(self.handle(arg, context))

        return new

    def handle_cxx_delete_expr(self, node, context):
        # Delete has no meaning.
        pass
    # def handle_cxx_unary_expr(self, node, context):
    # def handle_pack_expansion_expr(self, node, context):
    # def handle_size_of_pack_expr(self, node, context):
    # def handle_lambda_expr(self, node, context):
    # def handle_unexposed_stmt(self, node, context):
    # def handle_label_stmt(self, node, context):

    def handle_compound_stmt(self, node, context):
        if context.statements is None:
            context.statements = []
        for child in node.get_children():
            statement = self.handle(child, context)
            if statement:
                context.add_statement(statement)

    def handle_if_stmt(self, node, context):
        children = node.get_children()
        condition = self.handle(next(children), context)
        if_statement = If(condition, context)

        true_term = self.handle(next(children), if_statement.if_true)
        if true_term:
            if_statement.if_true.add_statement(true_term)

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
            if_false = Block(if_statement)
            false_term = self.handle(next(children), if_false)
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

    # def handle_switch_stmt(self, node, context):
    # def handle_case_stmt(self, node, context):
    # def handle_default_stmt(self, node, context):

    def handle_while_stmt(self, node, context):
        
        children = node.get_children()
        
        
        condition = self.handle(next(children), context)
        while_statement = While(condition, context)
        self.handle(next(children), while_statement.statements)
        
        try:
            next(children)
            raise Exception("Unexpected content in while statement")
        except StopIteration:
            pass

        return while_statement
        
    def handle_do_stmt(self, node, context):
        
        children = node.get_children()
        
        do_statement = Do(context)
        self.handle(next(children), do_statement.statements)
        do_statement.condition = self.handle(next(children), do_statement.statements)
        
        try:
            next(children)
            raise Exception("Unexpected content in do statement")
        except StopIteration:
            pass

        return do_statement

    def handle_for_stmt(self, node, context):
    
        children = node.get_children()
        child = next(children)
        
        init_stmt = None
        expr_stmt = None
        end_stmt = None
        
        # initial statement
        if child.kind == CursorKind.DECL_STMT:
            init_stmt = self.handle(child, context)
            child = next(children)
            
        if child.kind == CursorKind.BINARY_OPERATOR:
            expr_stmt = self.handle(child, context)
            child = next(children)
        
        if child.kind == CursorKind.UNARY_OPERATOR:
            end_stmt = self.handle(child, context)
            child = next(children)
        
        for_statement = For(init_stmt, expr_stmt, end_stmt, context)
        
        # content
        self.handle(child, for_statement.statements)
        
        try:
            next(children)
            raise Exception("Unexpected content in for statement")
        except StopIteration:
            pass

        return for_statement
        
    
        # decl
        # end
        # increment
        # content
        
    # def handle_goto_stmt(self, node, context):
    # def handle_indirect_goto_stmt(self, node, context):
    
    def handle_continue_stmt(self, node, context):
        # for loop cares if there's a continue
        end_expr = None
        parent = context
        while parent and not (isinstance(parent, (For, While, Do))):
            parent = parent.context
                              
        if isinstance(parent, For):
            end_expr = parent.end_expr
            
            
        return Continue(end_expr)
    
    def handle_break_stmt(self, node, context):
        return Break()

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
    
    def handle_null_stmt(self, node, context):
        pass
        
    def handle_decl_stmt(self, node, context):
        try:
            children = node.get_children()
            statement = self.handle(next(children), context)
        except StopIteration:
            pass

        try:
            self.handle(next(children), context)
            raise Exception("Don't know how to handle multiple statements")
        except StopIteration:
            pass

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
    def handle_cxx_final_attr(self, node, context):
        # No need to handle final declarations
        pass

    def handle_cxx_override_attr(self, node, context):
        # No need to handle override declarations
        pass

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
        pass

    def handle_macro_instantiation(self, node, context):
        # self.instantiated_macros[
        #     (node.location.file.name, node.location.line, node.location.column)
        # ] = self.macros.get(node.spelling, '')
        pass

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
    def __init__(self, verbosity):
        super(CodeDumper, self).__init__()
        self.verbosity = verbosity
        self.filenames = set()
        self.ignored_files = set()

    def parse(self, filenames, flags):
        abs_filenames = [os.path.abspath(f) for f in filenames]
        self.filenames.update(abs_filenames)
        source_filenames = [f for f in abs_filenames if os.path.splitext(f)[1] != '.h']

        self.tu = self.index.parse(
            None,
            args=source_filenames + flags,
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        )
        self.diagnostics(sys.stderr)

        self.handle(self.tu.cursor, 0)

    def handle(self, node, depth=0):
        if (node.location.file is None
                or os.path.abspath(node.location.file.name) in self.filenames):

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
        else:
            if node.location.file.name.startswith('/usr/include'):
                min_level = 2
            elif node.location.file.name.startswith('/usr/local'):
                min_level = 2
            else:
                min_level = 1

            if node.location.file.name not in self.ignored_files:
                if self.verbosity >= min_level:
                    print("Ignoring node in file %s" % node.location.file)
                self.ignored_files.add(node.location.file.name)


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
        '-std',
        help='The C/C++ standard to use (default: c++0x)',
        default='c++0x'
    )

    opts.add_argument(
        '-stdlib',
        help='The standard library to use (default: libstdc++)',
        default='libstdc++'
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
    dumper.parse(
        args.filename,
        flags=[
            '-I%s' % inc for inc in args.includes
        ] + [
            '-D%s' % define for define in args.defines
        ] + [
            '-std=%s' % args.std
        ] + [
            '-stdlib=%s' % args.stdlib
        ]

    )
