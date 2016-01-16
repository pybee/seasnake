from collections import namedtuple

from clang.cindex import Index


class ModuleDecl:
    def __init__(self, name):
        self.name = name
        self.statements = []
        self.imports = set()

    def add_declaration(self, decl):
        self.statements.append(decl)
        decl.add_imports(self)

    def add_import(self, module):
        self.imports.add(module)

    def output(self, out):
        if self.imports:
            for expr in sorted(self.imports):
                out.write(expr + '\n')
            out.write('\n\n')

        for expr in self.statements:
            expr.output(out)


EnumValue = namedtuple('EnumValue', ['key', 'value'])


class EnumDecl:
    def __init__(self, name):
        self.name = name
        self.enumerators = []

    def add_enumerator(self, entry):
        self.enumerators.append(entry)

    def add_imports(self, module):
        module.add_import('from enum import Enum')

    def output(self, out, depth=0):
        out.write('    ' * depth + "class %s(Enum):\n" % self.name)
        if self.enumerators:
            for enumerator in self.enumerators:
                out.write('    ' * (depth + 1) + "%s = %s\n" % (
                    enumerator.key, enumerator.value
                ))
        else:
            out.write('    pass\n')
        out.write('\n\n')


class Parameter:
    def __init__(self, name, ctype, default):
        self.name = name
        self.ctype = ctype
        self.default = default

    def add_to_context(self, context):
        context.add_parameter(self)


class FunctionDecl:
    def __init__(self, name):
        self.name = name
        self.parameters = []
        self.statements = []

    def add_parameter(self, parameter):
        self.parameters.append(parameter)

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
                statement.output(out, None)
                out.write('\n')
        else:
            out.write('    pass\n')
        out.write('\n\n')


class FunctionCall:
    def __init__(self, name):
        self.name = name
        self.arguments = []

    def add_argument(self, argument):
        self.arguments.append(argument)

    def add_imports(self, module):
        pass

    def output(self, out, depth=0):
        out.write('%s(' % self.name)
        if self.arguments:
            self.arguments[0].output(out, None)
            for arg in self.arguments[1:]:
                out.write(', ')
                arg.output(out, None)
        out.write(')')


class ClassDecl:
    def __init__(self, name):
        self.name = name
        self.superclass = None
        self.constructors = []
        self.destructors = []
        self.members = []
        self.methods = []

    def add_imports(self, module):
        if self.superclass:
            pass

    def output(self, out, depth=0):
        if self.superclass:
            out.write('    ' * depth + "class %s(%s):\n" % (self.name, self.superclass))
        else:
            out.write('    ' * depth + "class %s:\n" % self.name)
        if self.constructors or self.destructors or self.members or self.methods:
            for method in self.methods:
                method.write(out, depth+1)
        else:
            out.write('    pass\n')
        out.write('\n\n')


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
            out.write('\n')


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
            self.value.output(out, depth=None)


###########################################################################
# Expressions
###########################################################################

class Reference:
    def __init__(self, ref):
        self.ref = ref

    def add_imports(self, module):
        pass

    def output(self, out, depth=0):
        out.write(self.ref)


class VariableDeclaration:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def add_imports(self, module):
        pass

    def output(self, out, depth=0):
        out.write('%s = ' % self.name)
        self.value.output(out, depth)


class Literal:
    def __init__(self, value):
        self.value = value

    def add_imports(self, module):
        pass

    def output(self, out, depth=0):
        out.write(str(self.value))


class BinaryOperation:
    def add_imports(self, module):
        pass

    def output(self, out, depth=0):
        self.lvalue.output(out)
        out.write(' %s ' % self.op)
        self.rvalue.output(out)


###########################################################################
# Code generator
###########################################################################

class Generator:
    def __init__(self, name):
        self.index = Index.create(excludeDecls=True)
        self.module = ModuleDecl(name)

    def parse(self, filename):
        self.tu = self.index.parse(None, [filename])
        self.handle(self.tu.cursor, self.module)

    def parse_text(self, filename, content):
        self.tu = self.index.parse(filename, unsaved_files=[(filename, content)])
        self.handle(self.tu.cursor, self.module)

    def handle(self, node, context=None):
        try:
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
                self.add_declaration(decl)
        return klass

    def handle_enum_decl(self, node, context):
        enum = EnumDecl(node.spelling)
        for child in node.get_children():
            enum.add_enumerator(self.handle(child, enum))
        return enum

    # def handle_field_decl(self, node, context):

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
        value = next(node.get_children())
        if value:
            obj = self.handle(value, context)
            return VariableDeclaration(node.spelling, obj)

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
    # def handle_namespace(self, node, context):
    # def handle_linkage_spec(self, node, context):
    # def handle_constructor(self, node, context):
    # def handle_destructor(self, node, context):
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
    # def handle_member_ref(self, node, context):
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

    # def handle_member_ref_expr(self, node, context):
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
            context.add_declaration(self.handle(child, context))

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
