import argparse

from collections import namedtuple, OrderedDict

from clang.cindex import Index


class ModuleDecl:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.statements = []
        self.imports = set()
        self.submodules = {}

    @property
    def full_name(self):
        if self.parent:
            return '.'.join([self.parent.full_name, self.name])
        return self.name

    def add_to_context(self, context):
        context.add_submodule(self)

    def add_declaration(self, decl):
        self.statements.append(decl)
        decl.add_imports(self)

    def add_import(self, module):
        self.imports.add(module)

    def add_imports(self, module):
        pass

    def add_submodule(self, module):
        self.submodules[module.name, module]

    def output(self, out):
        if self.imports:
            for expr in sorted(self.imports):
                out.write(expr)
                out.clear_line()
            out.clear_block()

        for expr in self.statements:
            expr.output(out)

        for name, mod in self.submodules.items():
            print(mod.full_name)
            mod.output(out)


###########################################################################
# Enumerated types
###########################################################################


class EnumDecl:
    def __init__(self, name):
        self.name = name
        self.enumerators = []

    def add_enumerator(self, entry):
        self.enumerators.append(entry)

    def add_to_context(self, context):
        context.add_declaration(self)

    def add_imports(self, module):
        module.add_import('from enum import Enum')

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

class FunctionDecl:
    def __init__(self, name):
        self.name = name
        self.parameters = []
        self.statements = []

    def add_parameter(self, parameter):
        self.parameters.append(parameter)

    def add_to_context(self, context):
        context.add_declaration(self)

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


class Parameter:
    def __init__(self, name, ctype, default):
        self.name = name
        self.ctype = ctype
        self.default = default

    def add_to_context(self, context):
        context.add_parameter(self)


###########################################################################
# Classes
###########################################################################

class ClassDecl:
    def __init__(self, name):
        self.name = name
        self.superclass = None
        self.constructors = []
        self.destructors = []
        self.attrs = OrderedDict()
        self.methods = OrderedDict()
        self.classes = OrderedDict()

    def add_imports(self, module):
        if self.superclass:
            pass

    def add_declaration(self, klass):
        self.classes.append(klass)

    def add_constructor(self, klass):
        self.constructors.append(klass)

    def add_destructor(self, klass):
        self.destructors.append(klass)

    def add_attr(self, attr):
        self.attrs[attr.name] = attr

    def add_to_context(self, context):
        context.add_declaration(self)

    def output(self, out, depth=0):
        if self.superclass:
            out.write('    ' * depth + "class %s(%s):\n" % (self.name, self.superclass))
        else:
            out.write('    ' * depth + "class %s:\n" % self.name)
        if self.constructors or self.destructors or self.methods:
            for constructor in self.constructors:
                constructor.output(out, depth + 1)

            for destructor in self.destructors:
                destructor.output(out, depth + 1)

            for name, method in self.methods.items():
                method.output(out, depth + 1)
        else:
            out.write('    ' * (depth + 1) + 'pass')
        out.clear_block()


class Constructor:
    def __init__(self, klass):
        self.klass = klass
        self.parameters = []
        self.statements = []

    def add_parameter(self, parameter):
        self.parameters.append(parameter)

    def add_to_context(self, klass):
        klass.add_constructor(self)

    def add_attr(self, attr):
        self.klass.add_attr(attr)

    def add_imports(self, module):
        pass

    def add_statement(self, statement):
        self.statements.append(statement)
        statement.add_imports(self)

    def output(self, out, depth=0):
        if self.parameters:
            parameters = ', '.join(
                p.name if p.name else 'arg%s' % (i + 1)
                for i, p in enumerate(self.parameters))
            out.write('    ' * depth + "def __init__(self, %s):\n" % parameters)
        else:
            out.write('    ' * depth + "def __init__(self):\n")
        if self.klass.attrs or self.statements:
            for name, attr in self.klass.attrs.items():
                out.write('    ' * (depth + 1))
                attr.output(out)
                out.clear_line()

            for statement in self.statements:
                out.write('    ' * (depth + 1))
                statement.output(out)
                out.clear_line()
        else:
            out.write('    ' * (depth + 1) + 'pass')
        out.clear_block()


class Destructor:
    def __init__(self, klass):
        self.klass = klass
        self.parameters = []
        self.statements = []

    def add_to_context(self, klass):
        klass.add_constructor(self)

    def add_imports(self, module):
        pass

    def add_statement(self, statement):
        self.statements.append(statement)
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
        out.clear_block()


class Attribute:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def add_to_context(self, context):
        context.add_attr(self)

    def add_imports(self, module):
        pass

    def output(self, out):
        out.write('self.%s = ' % self.name)
        if self.value:
            self.value.output(out)
        else:
            out.write("None")
        out.clear_line()


###########################################################################
# Statements
###########################################################################

class Statement:
    def __init__(self):
        self.expressions = []

    def add_expression(self, expr):
        self.expressions.append(expr)
        expr.add_imports(self)

    def add_to_context(self, context):
        context.add_statement(self)

    def add_imports(self, module):
        pass

    def output(self, out, depth=0):
        for expr in self.expressions:
            expr.output(out, depth)
            out.clear_line()


class ReturnStatement:
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


class VariableDeclaration:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def add_to_context(self, context):
        context.add_declaration(self)

    def add_imports(self, module):
        pass

    def output(self, out, depth=0):
        out.write('%s = ' % self.name)
        if self.value:
            self.value.output(out)
        else:
            out.write('None')
        out.clear_line()


###########################################################################
# Expressions
###########################################################################

class Reference:
    def __init__(self, ref):
        self.ref = ref

    def add_imports(self, module):
        pass

    def output(self, out):
        out.write(self.ref)


class Literal:
    def __init__(self, value):
        self.value = value

    def add_imports(self, module):
        pass

    def output(self, out):
        out.write(str(self.value))


class BinaryOperation:
    def add_imports(self, module):
        pass

    def output(self, out):
        self.lvalue.output(out)
        out.write(' %s ' % self.op)
        self.rvalue.output(out)


class FunctionCall:
    def __init__(self, name):
        self.name = name
        self.arguments = []

    def add_argument(self, argument):
        self.arguments.append(argument)

    def add_imports(self, module):
        pass

    def output(self, out):
        out.write('%s(' % self.name)
        if self.arguments:
            self.arguments[0].output(out)
            for arg in self.arguments[1:]:
                out.write(', ')
                arg.output(out)
        out.write(')')


###########################################################################
# Code generator
###########################################################################

class CodeWriter:
    def __init__(self, out):
        self.out = out
        self.line_cleared = True
        self.block_cleared = True

    def write(self, content):
        self.out.write(content)
        self.line_cleared = False
        self.block_cleared = False

    def clear_line(self):
        if not self.line_cleared:
            self.out.write('\n')
            self.line_cleared = True

    def clear_block(self):
        self.clear_line()
        if not self.block_cleared:
            self.out.write('\n\n')
            self.block_cleared = True


class Generator:
    def __init__(self, name):
        self.index = Index.create(excludeDecls=True)
        self.module = ModuleDecl(name)

    def output(self, out):
        self.module.output(CodeWriter(out))

    def parse(self, filename):
        self.tu = self.index.parse(None, [filename])
        self.handle(self.tu.cursor, self.module)

    def parse_text(self, filename, content):
        self.tu = self.index.parse(filename, unsaved_files=[(filename, content)])
        self.handle(self.tu.cursor, self.module)

    def handle(self, node, context=None):
        try:
            # print(node.kind, node.spelling, [n.spelling for n in node.get_tokens()], [n.spelling for n in node.get_children()])
            handler = getattr(self, 'handle_%s' % node.kind.name.lower())
        except AttributeError:
            print("Ignoring node of type %s" % node.kind)
            handler = None

        if handler:
            return handler(node, context)

    # def handle_unexposed_decl(self, node, context):
    # def handle_struct_decl(self, node, context):
    # def handle_union_decl(self, node, context):
    def handle_class_decl(self, node, context):
        klass = ClassDecl(node.spelling)
        for child in node.get_children():
            decl = self.handle(child, klass)
            if decl:
                decl.add_to_context(klass)
        return klass

    def handle_enum_decl(self, node, context):
        enum = EnumDecl(node.spelling)
        for child in node.get_children():
            enum.add_enumerator(self.handle(child, enum))
        return enum

    def handle_field_decl(self, node, context):
        try:
            value = self.handle(next(node.get_children()), context)
            return Attribute(node.spelling, value)
        except StopIteration:
            return None
            # Alternatively; explicitly set to None.
            return Attribute(node.spelling)

    def handle_enum_constant_decl(self, node, enum):
        return EnumValue(node.spelling, node.enum_value)

    def handle_function_decl(self, node, context):
        function = FunctionDecl(node.spelling)
        for child in node.get_children():
            decl = self.handle(child, function)
            if decl:
                decl.add_to_context(function)
        return function

    def handle_var_decl(self, node, context):
        try:
            value = self.handle(next(node.get_children()), context)
            return VariableDeclaration(node.spelling, value)
        except:
            return None
            # Alternatively; explicitly set to None
            # return VariableDeclaration(node.spelling)

    def handle_parm_decl(self, node, context):
        # FIXME: need to pay attention to parameter declarations
        # that include an assignment.
        return Parameter(node.spelling, None, None)

    # def handle_objc_interface_decl(self, node, context):
    # def handle_objc_category_decl(self, node, context):
    # def handle_objc_protocol_decl(self, node, context):
    # def handle_objc_property_decl(self, node, context):
    # def handle_objc_ivar_decl(self, node, context):
    # def handle_objc_instance_method_decl(self, node, context):
    # def handle_objc_class_method_decl(self, node, context):
    # def handle_objc_implementation_decl(self, node, context):
    # def handle_objc_category_impl_decl(self, node, context):
    # def handle_typedef_decl(self, node, context):
    # def handle_cxx_method(self, node, context):
    def handle_namespace(self, node, context):
        mod = ModuleDecl(node.spelling, parent=context)

        for child in node.get_children():
            decl = self.handle(child, mod)
            if decl:
                decl.add_to_context(mod)

        return mod

    # def handle_linkage_spec(self, node, context):
    def handle_constructor(self, node, context):
        constructor = Constructor(context)
        constructor._children = node.get_children()

        for child in constructor._children:
            decl = self.handle(child, constructor)
            if decl:
                decl.add_to_context(constructor)

        return constructor

    def handle_destructor(self, node, context):
        destructor = Destructor(context)
        destructor._children = node.get_children()

        for child in destructor._children:
            decl = self.handle(child, destructor)
            if decl:
                decl.add_to_context(destructor)

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
    # def handle_objc_synthesize_decl(self, node, context):
    # def handle_objc_dynamic_decl(self, node, context):
    # def handle_cxx_access_spec_decl(self, node, context):
    # def handle_objc_super_class_ref(self, node, context):
    # def handle_objc_protocol_ref(self, node, context):
    # def handle_objc_class_ref(self, node, context):
    # def handle_type_ref(self, node, context):
    def handle_cxx_base_specifier(self, node, context):
        context.superclass = node.spelling.split(' ')[1]

    # def handle_template_ref(self, node, context):
    # def handle_namespace_ref(self, node, context):
    def handle_member_ref(self, node, context):
        attr = Attribute(node.spelling)
        child = next(context._children)
        attr.value = self.handle(child, attr)
        return attr

    # def handle_label_ref(self, node, context):
    # def handle_overloaded_decl_ref(self, node, context):
    # def handle_variable_ref(self, node, context):
    # def handle_invalid_file(self, node, context):
    # def handle_no_decl_found(self, node, context):
    # def handle_not_implemented(self, node, context):
    # def handle_invalid_code(self, node, context):
    def handle_unexposed_expr(self, node, statement):
        return Reference(node.spelling)

    def handle_decl_ref_expr(self, node, statement):
        return Reference(node.spelling)

    def handle_member_ref_expr(self, node, context):
        return Reference("self." + node.spelling)

    def handle_call_expr(self, node, context):
        children = node.get_children()
        fn = FunctionCall(next(children).spelling)

        for child in children:
            fn.add_argument(self.handle(child, fn))

        return fn

    # def handle_objc_message_expr(self, node, context):
    # def handle_block_expr(self, node, context):
    def handle_integer_literal(self, node, context):
        return Literal(int(next(node.get_tokens()).spelling))

    def handle_floating_literal(self, node, context):
        return Literal(float(next(node.get_tokens()).spelling))

    # def handle_imaginary_literal(self, node, context):
    # def handle_string_literal(self, node, context):
    # def handle_character_literal(self, node, context):
    # def handle_paren_expr(self, node, context):
    # def handle_unary_operator(self, node, context):
    # def handle_array_subscript_expr(self, node, context):
    def handle_binary_operator(self, node, context):
        binop = BinaryOperation()
        children = node.get_children()

        lnode = next(children)
        binop.lvalue = self.handle(lnode, binop)

        binop.op = list(lnode.get_tokens())[-1].spelling

        rnode = next(children)
        binop.rvalue = self.handle(rnode, binop)

        return binop

    # def handle_compound_assignment_operator(self, node, context):
    # def handle_conditional_operator(self, node, context):
    # def handle_cstyle_cast_expr(self, node, context):
    # def handle_compound_literal_expr(self, node, context):
    # def handle_init_list_expr(self, node, context):
    # def handle_addr_label_expr(self, node, context):
    # def handle_stmtexpr(self, node, context):
    # def handle_generic_selection_expr(self, node, context):
    # def handle_gnu_null_expr(self, node, context):
    # def handle_cxx_static_cast_expr(self, node, context):
    # def handle_cxx_dynamic_cast_expr(self, node, context):
    # def handle_cxx_reinterpret_cast_expr(self, node, context):
    # def handle_cxx_const_cast_expr(self, node, context):
    # def handle_cxx_functional_cast_expr(self, node, context):
    # def handle_cxx_typeid_expr(self, node, context):
    # def handle_cxx_bool_literal_expr(self, node, context):
    # def handle_cxx_this_expr(self, node, context):
    # def handle_cxx_throw_expr(self, node, context):
    # def handle_cxx_new_expr(self, node, context):
    # def handle_cxx_delete_expr(self, node, context):
    # def handle_cxx_unary_expr(self, node, context):
    # def handle_objc_string_literal(self, node, context):
    # def handle_objc_encode_expr(self, node, context):
    # def handle_objc_selector_expr(self, node, context):
    # def handle_objc_protocol_expr(self, node, context):
    # def handle_objc_bridge_cast_expr(self, node, context):
    # def handle_pack_expansion_expr(self, node, context):
    # def handle_size_of_pack_expr(self, node, context):
    # def handle_lambda_expr(self, node, context):
    # def handle_obj_bool_literal_expr(self, node, context):
    # def handle_obj_self_expr(self, node, context):
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
        retval = ReturnStatement()
        try:
            retval.value = self.handle(next(node.get_children()), retval)
        except:
            pass

        return retval

    # def handle_asm_stmt(self, node, context):
    # def handle_objc_at_try_stmt(self, node, context):
    # def handle_objc_at_catch_stmt(self, node, context):
    # def handle_objc_at_finally_stmt(self, node, context):
    # def handle_objc_at_throw_stmt(self, node, context):
    # def handle_objc_at_synchronized_stmt(self, node, context):
    # def handle_objc_autorelease_pool_stmt(self, node, context):
    # def handle_objc_for_collection_stmt(self, node, context):
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
            return self.handle(next(node.get_children()), context)
        except StopIteration:
            pass
        except:
            raise Exception("Don't know how to handle multiple statements")

    def handle_translation_unit(self, node, context):
        for child in node.get_children():
            decl = self.handle(child, context)
            if decl:
                context.add_declaration(decl)

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
    # def handle_macro_definition(self, node, context):
    # def handle_macro_instantiation(self, node, context):
    # def handle_inclusion_directive(self, node, context):
    # def handle_module_import_decl(self, node, context):
    # def handle_type_alias_template_decl(self, node, context):


# A simpler version of Generator that just
# dumps the tree structure.
class Dumper:
    def __init__(self):
        self.index = Index.create(excludeDecls=True)

    def parse(self, filename):
        self.tu = self.index.parse(None, [filename])
        print('===', filename)
        self.handle(self.tu.cursor, 1)

    def handle(self, node, depth=0):
        print(
            '    ' * depth,
            node.kind,
            node.spelling,
            repr(list(n.spelling for n in node.get_tokens()))
        )

        for child in node.get_children():
            self.handle(child, depth + 1)

if __name__ == '__main__':
    opts = argparse.ArgumentParser(
        description='Display AST structure for C++ file.',
    )

    opts.add_argument(
        'filename',
        metavar='file.cpp',
        help='The file(s) to dump.',
        nargs="+"
    )

    args = opts.parse_args()

    dumper = Dumper()
    for filename in args.filename:
        dumper.parse(filename)
