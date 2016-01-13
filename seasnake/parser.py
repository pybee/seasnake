import os
import sys

from ply import yacc

# from . import c_ast
from seasnake.lexer import CppLexer
# from .plyparser import PLYParser, Coord, ParseError
# from .ast_transforms import fix_switch_cases


class Coord(object):
    """ Coordinates of a syntactic element. Consists of:
            - File name
            - Line number
            - (optional) column number, for the Lexer
    """
    __slots__ = ('file', 'line', 'column', '__weakref__')

    def __init__(self, file, line, column=None):
        self.file = file
        self.line = line
        self.column = column

    def __str__(self):
        if self.file:
            output = "%s, line %s" % (self.file, self.line)
        else:
            output = "Line %s" % self.line
        if self.column:
            output += ", column %s" % self.column
        return output


class CppParser(object):
    def __init__(self):
        self.clex = CppLexer(
            error_func=self._lex_error_func,
            on_lbrace_func=self._lex_on_lbrace_func,
            on_rbrace_func=self._lex_on_rbrace_func,
            type_lookup_func=self._lex_type_lookup_func)

        # self.clex.build(
        #     optimize=lex_optimize,
        #     lextab=lextab,
        #     outputdir=taboutputdir)
        # self.tokens = self.clex.tokens

        # self.cparser = yacc.yacc(
        #     module=self,
        #     start='translation_unit_or_empty',
        #     # debug=yacc_debug,
        #     # optimize=yacc_optimize,
        #     # tabmodule=yacctab,
        #     # outputdir=taboutputdir,
        # )

        # Stack of scopes for keeping track of symbols. _scope_stack[-1] is
        # the current (topmost) scope. Each scope is a dictionary that
        # specifies whether a name is a type. If _scope_stack[n][name] is
        # True, 'name' is currently a type in the scope. If it's False,
        # 'name' is used in the scope but not as a type (for instance, if we
        # saw: int name;
        # If 'name' is not a key in _scope_stack[n] then 'name' was not defined
        # in this scope at all.
        self._scope_stack = [dict()]

        # # Keeps track of the last token given to yacc (the lookahead token)
        self._last_yielded_token = None

        self.clex.build(
            optimize=False,
            lextab='seasnake.compiler_lex_table',
            outputdir=os.path.dirname(__file__)
        )
        self.tokens = self.clex.tokens

        self.cparser = yacc.yacc(
            module=self,
            start='translation_unit',
            debug=True,
            optimize=False,
            tabmodule='seasnake.compiler_yacc_table',
            outputdir=os.path.dirname(__file__)
        )

        # self.clex.input(data)
        # token = self.clex.token()
        # while token:
        #     # print(token.value, end='')
        #     print(token)
        #     token = self.clex.token()

    def _coord(self, lineno, column=None):
        return Coord(
            file=self.clex.filename,
            line=lineno,
            column=column
        )

    def _parse_error(self, msg, coord):
        raise Exception("%s: %s" % (coord, msg))

    def parse(self, text, filename='', debuglevel=0):
        """ Parses C++ code and returns an AST.

            text:
                A string containing the C++ source code

            filename:
                Name of the file being parsed (for meaningful
                error messages)

            debuglevel:
                Debug level to yacc
        """
        self.clex.filename = filename
        self.clex.reset_lineno()
        self._scope_stack = [dict()]
        self._last_yielded_token = None
        return self.cparser.parse(
            input=text,
            lexer=self.clex,
            debug=debuglevel
        )

    ######################--   PRIVATE   --######################

    def _push_scope(self):
        self._scope_stack.append(dict())

    def _pop_scope(self):
        assert len(self._scope_stack) > 1
        self._scope_stack.pop()

    def _add_typedef_name(self, name, coord):
        """ Add a new typedef name (ie a TYPEID) to the current scope
        """
        if not self._scope_stack[-1].get(name, True):
            self._parse_error(
                "Typedef %r previously declared as non-typedef "
                "in this scope" % name, coord)
        self._scope_stack[-1][name] = True

    def _add_identifier(self, name, coord):
        """ Add a new object, function, or enum member name (ie an ID) to the
            current scope
        """
        if self._scope_stack[-1].get(name, False):
            self._parse_error(
                "Non-typedef %r previously declared as typedef "
                "in this scope" % name, coord)
        self._scope_stack[-1][name] = False

    def _is_type_in_scope(self, name):
        """ Is *name* a typedef-name in the current scope?
        """
        for scope in reversed(self._scope_stack):
            # If name is an identifier in this scope it shadows typedefs in
            # higher scopes.
            in_scope = scope.get(name)
            if in_scope is not None:
                return in_scope
        return False

    def _lex_error_func(self, msg, line, column):
        self._parse_error(msg, self._coord(line, column))

    def _lex_on_lbrace_func(self):
        self._push_scope()

    def _lex_on_rbrace_func(self):
        self._pop_scope()

    def _lex_type_lookup_func(self, name):
        """ Looks up types that were previously defined with
            typedef.
            Passed to the lexer for recognizing identifiers that
            are types.
        """
        # is_type = self._is_type_in_scope(name)
        # return is_type
        print("Lookup func", name)
        return None

    def _get_yacc_lookahead_token(self):
        """ We need access to yacc's lookahead token in certain cases.
            This is the last token yacc requested from the lexer, so we
            ask the lexer.
        """
        return self.clex.last_token

    ##
    ## Precedence and associativity of operators
    ##
    precedence = (
        ('nonassoc', 'SHIFT_THERE'),
        ('nonassoc', 'SCOPE', 'ELSE', 'INC', 'DEC', '+', '-', '*', '&', '[', '{', '<', ':', 'STRING_LITERAL'),
        ('nonassoc', 'REDUCE_HERE_MOSTLY'),
        ('nonassoc', '('),
        # ('nonassoc', 'REDUCE_HERE'),
    )

    ###########################################################################
    # The following grammar is derived from
    # http://www.computing.surrey.ac.uk/research/dsrg/fog/
    ###########################################################################

    # The %prec resolves the $014.2-3 ambiguity: Identifier '<' is forced to go
    # through the is-it-a-template-name test All names absorb TEMPLATE with the
    # name, so that no template_test is performed for them. This requires all
    # potential declarations within an expression to perpetuate this policy and
    # thereby guarantee the ultimate coverage of explicit_instantiation.

    # The %prec also resolves a conflict in identifier : which is forced to be a
    # shift of a label for a labeled-statement rather than a reduction for the
    # name of a bit-field or generalised constructor. This is pretty dubious
    # syntactically but correct for all semantic possibilities. The shift is
    # only activated when the ambiguity exists at the start of a statement. In
    # this context a bit-field declaration or constructor definition are not
    # allowed.

    def p_identifier(self, p):
        """identifier : IDENTIFIER
        """
        # { $$ = $1; }

    def p_id(self, p):
        """id : identifier %prec SHIFT_THERE
              | identifier template_test '+' template_argument_list '>'
              | identifier template_test '-'
              | template_id
        """
        # /* Force < through test */ { $$ = YACC_NAME($1); }
        # { $$ = YACC_TEMPLATE_NAME($1, $4); }
        # /* requeued < follows */  { $$ = YACC_NAME($1); }

    def p_template_test(self, p):
        """template_test : '<'
        """
        # { template_test(); }

    def p_global_scope(self, p):
        """global_scope : SCOPE
                        | TEMPLATE global_scope
        """
        # { $$ = 0; }
        # { $$ = YACC_SET_TEMPLATE_SCOPE($2); }

    def p_id_scope(self, p):
        """id_scope : id SCOPE
        """
        # { $$ = YACC_NESTED_SCOPE($1); }

    def p_nested_id(self, p):
        """nested_id : id %prec SHIFT_THERE
                     | id_scope nested_id
        """
        # /* Maximise length */
        # { $$ = YACC_NESTED_ID($1, $2); }

    def p_scoped_id(self, p):
        """scoped_id : nested_id
                     | global_scope nested_id
        """
        #
        # { $$ = YACC_SCOPED_ID($1, $2); }

    # destructor_id has to be held back to avoid a conflict with a one's
    # complement as per $05.3.1-9, It gets put back only when scoped or in a
    # declarator_id, which is only used as an explicit member name. Declarations
    # of an unscoped destructor are always parsed as a one's complement.
    def p_destructor_id(self, p):
        """destructor_id : '~' id
                         | TEMPLATE destructor_id
        """
        # { $$ = YACC_DESTRUCTOR_ID($2); }
        # { $$ = YACC_SET_TEMPLATE_ID($2); }

    def p_special_function_id(self, p):
        """special_function_id : conversion_function_id
                               | operator_function_id
                               | TEMPLATE special_function_id
        """
        #
        #
        # { $$ = YACC_SET_TEMPLATE_ID($2); }

    def p_nested_special_function_id(self, p):
        """nested_special_function_id : special_function_id
                                      | id_scope destructor_id
                                      | id_scope nested_special_function_id
        """
        #
        #{ $$ = YACC_NESTED_ID($1, $2); }
        #{ $$ = YACC_NESTED_ID($1, $2); }

    def p_scoped_special_function_id(self, p):
        """scoped_special_function_id : nested_special_function_id
                                      | global_scope nested_special_function_id
        """
        #
        # { $$ = YACC_SCOPED_ID($1, $2); }

    # declarator-id is all names in all scopes, except reserved words
    def p_declarator_id(self, p):
        """declarator_id : scoped_id
                         | scoped_special_function_id
                         | destructor_id
        """

    # The standard defines pseudo-destructors in terms of type-name, which is
    # class/enum/typedef, of which class-name is covered by a normal destructor.
    # pseudo-destructors are supposed to support ~int() in templates, so the
    # grammar here covers built-in names. Other names are covered by the lack of
    # identifier/type discrimination.
    def p_built_in_type_id(self, p):
        """built_in_type_id : built_in_type_specifier
                            | built_in_type_id built_in_type_specifier
        """
        #
        # { $$ = YACC_BUILT_IN_IDS($1, $2); }

    def p_pseudo_destructor_id(self, p):
        """pseudo_destructor_id : built_in_type_id SCOPE '~' built_in_type_id
                                | '~' built_in_type_id
                                | TEMPLATE pseudo_destructor_id
        """
        # { $$ = YACC_PSEUDO_DESTRUCTOR_ID($1, $4); }
        # { $$ = YACC_PSEUDO_DESTRUCTOR_ID(0, $2); }
        # { $$ = YACC_SET_TEMPLATE_ID($2); }

    def p_nested_pseudo_destructor_id(self, p):
        """nested_pseudo_destructor_id : pseudo_destructor_id
                                       | id_scope nested_pseudo_destructor_id
        """
        # { $$ = YACC_NESTED_ID($1, $2); }

    def p_scoped_pseudo_destructor_id(self, p):
        """scoped_pseudo_destructor_id : nested_pseudo_destructor_id
                                       | global_scope scoped_pseudo_destructor_id
        """
        # { $$ = YACC_SCOPED_ID($1, $2); }

    # -------------------------------------------------------------------------
    # A.2 Lexical conventions
    # -------------------------------------------------------------------------
    #
    # String concatenation is a phase 6, not phase 7 activity so does not
    # really belong in the grammar. However it may be convenient to have it
    # here to make this grammar fully functional. Unfortunately it introduces
    # a conflict with the generalised parsing of extern "C" which is correctly
    # resolved to maximise the string length as the token source should do
    # anyway.

    def p_string(self, p):
        """string : STRING_LITERAL
        """
        # { $$ = YACC_STRINGS($1, 0); }

    def p_literal(self, p):
        """literal : INTEGER_LITERAL
                   | CHARACTER_LITERAL
                   | FLOAT_LITERAL
                   | string
                   | boolean_literal
        """
        # { $$ = YACC_INTEGER_LITERAL_EXPRESSION($1); }
        # { $$ = YACC_CHARACTER_LITERAL_EXPRESSION($1); }
        # { $$ = YACC_FLOATING_LITERAL_EXPRESSION($1); }
        # { $$ = YACC_STRING_LITERAL_EXPRESSION($1); }

    def p_boolean_literal(self, p):
        """boolean_literal : FALSE
                           | TRUE
        """
        # { $$ = YACC_FALSE_EXPRESSION(); }
        # { $$ = YACC_TRUE_EXPRESSION(); }

    #--------------------------------------------------------------------------
    # A.3 Basic concepts
    #--------------------------------------------------------------------------

    def p_translation_unit(self, p):
        """translation_unit : declaration_seq_opt
        """
        # { YACC_RESULT($1); }

    #--------------------------------------------------------------------------
    # A.4 Expressions
    #--------------------------------------------------------------------------

    # primary_expression covers an arbitrary sequence of all names with the
    # exception of an unscoped destructor, which is parsed as its unary
    # expression which is the correct disambiguation (when ambiguous). This
    # eliminates the traditional A(B) meaning A B ambiguity, since we never
    # have to tack an A onto the front of something that might start with (.
    # The name length got maximised ab initio. The downside is that semantic
    # interpretation must split the names up again.
    #
    # Unification of the declaration and expression syntax means that unary
    # and binary pointer declarator operators:
    #
    #     int * * name
    #
    # are parsed as binary and unary arithmetic operators (int) * (*name).
    # Since type information is not used ambiguities resulting from a cast
    #
    #     (cast)*(value)
    #
    # are resolved to favour the binary rather than the cast unary to ease AST
    # clean-up. The cast-call ambiguity must be resolved to the cast to ensure
    # that (a)(b)c can be parsed.
    #
    # The problem of the functional cast ambiguity
    #
    #     name(arg)
    #
    # as call or declaration is avoided by maximising the name within the
    # parsing kernel. So primary_id_expression picks up
    #
    #     extern long int const var = 5;
    #
    # as an assignment to the syntax parsed as "extern long int const var".
    # The presence of two names is parsed so that "extern long into const" is
    # distinguished from "var" considerably simplifying subsequent semantic
    # resolution.
    #
    # The generalised name is a concatenation of potential type-names (scoped
    # identifiers or built-in sequences) plus optionally one of the special
    # names such as an operator-function-id, conversion-function-id or
    # destructor as the final name.
    def p_primary_expression(self, p):
        """primary_expression : literal
                              | THIS
                              | suffix_decl_specified_ids
                              | abstract_expression %prec REDUCE_HERE_MOSTLY
        """
        #{ $$ = YACC_THIS_EXPRESSION(); }
        #
        #{ $$ = $1; }
        #

        # /*  |                               SCOPE identifier                                            -- covered by suffix_decl_specified_ids */
        # /*  |                               SCOPE operator_function_id                                  -- covered by suffix_decl_specified_ids */
        # /*  |                               SCOPE qualified_id                                          -- covered by suffix_decl_specified_ids */
        # /*  |                               id_expression                                               -- covered by suffix_decl_specified_ids */

    # Abstract-expression covers the () and [] of abstract-declarators.
    def p_abstract_expression(self, p):
        """abstract_expression : parenthesis_clause
                               | '[' expression_opt ']'
                               | TEMPLATE abstract_expression
        """
        # { $$ = YACC_ABSTRACT_FUNCTION_EXPRESSION($1); }
        # { $$ = YACC_ABSTRACT_ARRAY_EXPRESSION($2); }
        # { $$ = YACC_SET_TEMPLATE_EXPRESSION($2); }

    # Type I function parameters are ambiguous with respect to the generalised
    # name, so we have to do a lookahead following any function-like
    # parentheses. This unfortunately hits normal code, so kill the -- lines
    # and add the ++ lines for efficiency. Supporting Type I code under the
    # superset causes perhaps 25% of lookahead parsing. Sometimes complete
    # class definitions get traversed since they are valid generalised type I
    # parameters!
    def p_type1_parameters(self, p):
        """type1_parameters : parameter_declaration_list ';'
                            | type1_parameters parameter_declaration_list ';'
        """
        # { $$ = YACC_TYPE1_PARAMETERS(0, $1); }
        # { $$ = YACC_TYPE1_PARAMETERS($1, $2); }

    def p_mark_type1(self, p):
        """mark_type1 :
        """
        # { $$ = mark_type1(); yyclearin; }

    def p_postfix_expression(self, p):
        """postfix_expression : primary_expression
                              | postfix_expression parenthesis_clause mark_type1 '-'
                              | postfix_expression parenthesis_clause mark_type1 '+' type1_parameters mark '{' error
                              | postfix_expression parenthesis_clause mark_type1 '+' type1_parameters mark error
                              | postfix_expression parenthesis_clause mark_type1 '+' error
                              | postfix_expression '[' expression_opt ']'
                              | postfix_expression '.' declarator_id
                              | postfix_expression '.' scoped_pseudo_destructor_id
                              | postfix_expression ARROW declarator_id
                              | postfix_expression ARROW scoped_pseudo_destructor_id
                              | postfix_expression INC
                              | postfix_expression DEC
                              | DYNAMIC_CAST '<' type_id '>' '(' expression ')'
                              | STATIC_CAST '<' type_id '>' '(' expression ')'
                              | REINTERPRET_CAST '<' type_id '>' '(' expression ')'
                              | CONST_CAST '<' type_id '>' '(' expression ')'
                              | TYPEID parameters_clause
        """
        # { $$ = YACC_CALL_EXPRESSION($1, $2); }
        # { yyerrok; yyclearin; remark_type1($6); unmark(); unmark($5); $$ = YACC_TYPE1_EXPRESSION($1, $2, $5); }
        # { yyerrok; yyclearin; remark_type1($3); unmark(); unmark(); $$ = YACC_CALL_EXPRESSION($1, $2); }
        # { yyerrok; yyclearin; remark_type1($3); unmark(); $$ = YACC_CALL_EXPRESSION($1, $2); }
        # { $$ = YACC_ARRAY_EXPRESSION($1, $3); }
        # { $$ = YACC_DOT_EXPRESSION($1, $3); }
        # { $$ = YACC_DOT_EXPRESSION($1, $3); }
        # { $$ = YACC_ARROW_EXPRESSION($1, $3); }
        # { $$ = YACC_ARROW_EXPRESSION($1, $3); }
        # { $$ = YACC_POST_INCREMENT_EXPRESSION($1); }
        # { $$ = YACC_POST_DECREMENT_EXPRESSION($1); }
        # { $$ = YACC_DYNAMIC_CAST_EXPRESSION($3, $6); }
        # { $$ = YACC_STATIC_CAST_EXPRESSION($3, $6); }
        # { $$ = YACC_REINTERPRET_CAST_EXPRESSION($3, $6); }
        # { $$ = YACC_CONST_CAST_EXPRESSION($3, $6); }
        # { $$ = YACC_TYPEID_EXPRESSION($2); }

    def p_expression_list_1(self, p):
        """expression_list_opt :
                               | expression_list
        """
        # { $$ = YACC_EXPRESSIONS(0, 0); }
        #

    def p_expression_list_2(self, p):
        """expression_list : assignment_expression
                           | expression_list ',' assignment_expression
        """
        # { $$ = YACC_EXPRESSIONS(0, $1); }
        # { $$ = YACC_EXPRESSIONS($1, $3); }

    def p_unary_expression(self, p):
        """unary_expression : postfix_expression
                            | INC cast_expression
                            | DEC cast_expression
                            | ptr_operator cast_expression
                            | suffix_decl_specified_scope star_ptr_operator cast_expression
                            | '+' cast_expression
                            | '-' cast_expression
                            | '!' cast_expression
                            | '~' cast_expression
                            | SIZEOF unary_expression
                            | new_expression
                            | global_scope new_expression
                            | delete_expression
                            | global_scope delete_expression
        """
        # { $$ = YACC_PRE_INCREMENT_EXPRESSION($2); }
        # { $$ = YACC_PRE_DECREMENT_EXPRESSION($2); }
        # { $$ = YACC_POINTER_EXPRESSION($1, $2); }
        # { $$ = YACC_SCOPED_POINTER_EXPRESSION($1, $2, $3); }
        # { $$ = YACC_PLUS_EXPRESSION($2); }
        # { $$ = YACC_MINUS_EXPRESSION($2); }
        # { $$ = YACC_NOT_EXPRESSION($2); }
        # { $$ = YACC_COMPLEMENT_EXPRESSION($2); }
        # { $$ = YACC_SIZEOF_EXPRESSION($2); }
        #
        # { $$ = YACC_GLOBAL_EXPRESSION($2); }
        #
        # { $$ = YACC_GLOBAL_EXPRESSION($2); }

    def p_delete_expression(self, p):
        """delete_expression : DELETE cast_expression
        """
        # { $$ = YACC_DELETE_EXPRESSION($2); }

    def p_new_expression(self, p):
        """new_expression : NEW new_type_id new_initializer_opt
                          | NEW parameters_clause new_type_id new_initializer_opt
                          | NEW parameters_clause
                          | NEW parameters_clause parameters_clause new_initializer_opt
        """
        # { $$ = YACC_NEW_TYPE_ID_EXPRESSION(0, $2, $3); }
        # { $$ = YACC_NEW_TYPE_ID_EXPRESSION($2, $3, $4); }
        # { $$ = YACC_NEW_EXPRESSION($2, 0, 0); }
        # { $$ = YACC_NEW_EXPRESSION($2, $3, $4); }

    def p_new_type_id(self, p):
        """new_type_id : type_specifier ptr_operator_seq_opt
                       | type_specifier new_declarator
                       | type_specifier new_type_id
        """
        # { $$ = YACC_TYPED_EXPRESSION($1, $2); }
        # { $$ = YACC_TYPED_EXPRESSION($1, $2); }
        # { $$ = YACC_TYPED_EXPRESSION($1, $2); }

    def p_new_declarator(self, p):
        """new_declarator : ptr_operator new_declarator
                          | direct_new_declarator
        """
        # { $$ = YACC_POINTER_EXPRESSION($1, $2); }

    def p_direct_new_declarator(self, p):
        """direct_new_declarator : '[' expression ']'
                                 | direct_new_declarator '[' constant_expression ']'
        """
        # { $$ = YACC_ABSTRACT_ARRAY_EXPRESSION($2); }
        # { $$ = YACC_ARRAY_EXPRESSION($1, $3); }

    def p_new_initializer(self, p):
        """new_initializer_opt :
                               | '(' expression_list_opt ')'
        """
        # { $$ = YACC_EXPRESSIONS(0, 0); }
        # { $$ = $2; }

    # cast-expression is generalised to support a [] as well as a () prefix.
    # This covers the omission of DELETE[] which when followed by a
    # parenthesised expression was ambiguous. It also covers the gcc indexed
    # array initialisation for free.
    def p_cast_expression(self, p):
        """cast_expression : unary_expression
                           | abstract_expression cast_expression
        """
        #
        # { $$ = YACC_CAST_EXPRESSION($1, $2); }

    def p_pm_expression(self, p):
        """pm_expression : cast_expression
                         | pm_expression DOT_STAR cast_expression
                         | pm_expression ARROW_STAR cast_expression
        """
        # { $$ = YACC_DOT_STAR_EXPRESSION($1, $3); }
        # { $$ = YACC_ARROW_STAR_EXPRESSION($1, $3); }

    def p_multiplicative_expression(self, p):
        """multiplicative_expression : pm_expression
                                     | multiplicative_expression star_ptr_operator pm_expression
                                     | multiplicative_expression '/' pm_expression
                                     | multiplicative_expression '%' pm_expression
        """
        #
        # { $$ = YACC_MULTIPLY_EXPRESSION($1, $2, $3); }
        # { $$ = YACC_DIVIDE_EXPRESSION($1, $3); }
        # { $$ = YACC_MODULUS_EXPRESSION($1, $3); }

    def p_additive_expression(self, p):
        """additive_expression : multiplicative_expression
                               | additive_expression '+' multiplicative_expression
                               | additive_expression '-' multiplicative_expression
        """
        # { $$ = YACC_ADD_EXPRESSION($1, $3); }
        # { $$ = YACC_SUBTRACT_EXPRESSION($1, $3); }

    def p_shift_expression(self, p):
        """shift_expression : additive_expression
                            | shift_expression SHL additive_expression
                            | shift_expression SHR additive_expression
        """
        # { $$ = YACC_SHIFT_LEFT_EXPRESSION($1, $3); }
        # { $$ = YACC_SHIFT_RIGHT_EXPRESSION($1, $3); }

    def p_relational_expression(self, p):
        """relational_expression : shift_expression
                                 | relational_expression '<' shift_expression
                                 | relational_expression '>' shift_expression
                                 | relational_expression LE shift_expression
                                 | relational_expression GE shift_expression
        """
        # { $$ = YACC_LESS_THAN_EXPRESSION($1, $3); }
        # { $$ = YACC_GREATER_THAN_EXPRESSION($1, $3); }
        # { $$ = YACC_LESS_EQUAL_EXPRESSION($1, $3); }
        # { $$ = YACC_GREATER_EQUAL_EXPRESSION($1, $3); }

    def p_equality_expression(self, p):
        """equality_expression : relational_expression
                               | equality_expression EQ relational_expression
                               | equality_expression NE relational_expression
        """
        # { $$ = YACC_EQUAL_EXPRESSION($1, $3); }
        # { $$ = YACC_NOT_EQUAL_EXPRESSION($1, $3); }

    def p_and_expression(self, p):
        """and_expression : equality_expression
                          | and_expression '&' equality_expression
        """
        #
        # { $$ = YACC_AND_EXPRESSION($1, $3); }

    def p_exclusive_or_expression(self, p):
        """exclusive_or_expression : and_expression
                                   | exclusive_or_expression '^' and_expression
        """
        # { $$ = YACC_EXCLUSIVE_OR_EXPRESSION($1, $3); }

    def p_inclusive_or_expression(self, p):
        """inclusive_or_expression : exclusive_or_expression
                                   | inclusive_or_expression '|' exclusive_or_expression
        """
        # { $$ = YACC_INCLUSIVE_OR_EXPRESSION($1, $3); }

    def p_logical_and_expression(self, p):
        """logical_and_expression : inclusive_or_expression
                                  | logical_and_expression LOG_AND inclusive_or_expression
        """
        # { $$ = YACC_LOGICAL_AND_EXPRESSION($1, $3); }

    def p_logical_or_expression(self, p):
        """logical_or_expression : logical_and_expression
                                 | logical_or_expression LOG_OR logical_and_expression
        """
        # { $$ = YACC_LOGICAL_OR_EXPRESSION($1, $3); }

    def p_conditional_expression(self, p):
        """conditional_expression : logical_or_expression
                                  | logical_or_expression '?' expression ':' assignment_expression
        """
        # { $$ = YACC_CONDITIONAL_EXPRESSION($1, $3, $5); }

    # assignment-expression is generalised to cover the simple assignment of a
    # braced initializer in order to contribute to the coverage of parameter-
    # declaration and init-declaration.
    def p_assignment_expression(self, p):
        """assignment_expression : conditional_expression
                                 | logical_or_expression assignment_operator assignment_expression
                                 | logical_or_expression '=' braced_initializer
                                 | throw_expression

        """
        #
        # { $$ = YACC_ASSIGNMENT_EXPRESSION($1, $2, $3); }
        # { $$ = YACC_ASSIGNMENT_EXPRESSION($1, $2, $3); }
        #

    def p_assignment_operator(self, p):
        """assignment_operator : '='
                               | ASS_ADD
                               | ASS_AND
                               | ASS_DIV
                               | ASS_MOD
                               | ASS_MUL
                               | ASS_OR
                               | ASS_SHL
                               | ASS_SHR
                               | ASS_SUB
                               | ASS_XOR
        """

    # expression is widely used and usually single-element, so the reductions
    # are arranged so that a single-element expression is returned as is.
    # Multi- element expressions are parsed as a list that may then behave
    # polymorphically as an element or be compacted to an element.
    def p_expression_1(self, p):
        """expression_opt :
                          | expression
        """
        # { $$ = YACC_EXPRESSION(0); }

    def p_expression_2(self, p):
        """expression : assignment_expression
                      | expression_list ',' assignment_expression
        """
        # { $$ = YACC_EXPRESSION(YACC_EXPRESSIONS($1, $3)); }

    def p_constant_expression(self, p):
        """constant_expression : conditional_expression
        """

    # The grammar is repeated for when the parser stack knows that the next > must end a template.
    def p_templated_relational_expression(self, p):
        """templated_relational_expression : shift_expression
                                           | templated_relational_expression '<' shift_expression
                                           | templated_relational_expression LE shift_expression
                                           | templated_relational_expression GE shift_expression
        """
        #
        # { $$ = YACC_LESS_THAN_EXPRESSION($1, $3); }
        # { $$ = YACC_LESS_EQUAL_EXPRESSION($1, $3); }
        # { $$ = YACC_GREATER_EQUAL_EXPRESSION($1, $3); }

    def p_templated_equality_expression(self, p):
        """templated_equality_expression : templated_relational_expression
                                         | templated_equality_expression EQ templated_relational_expression
                                         | templated_equality_expression NE templated_relational_expression
        """
        # { $$ = YACC_EQUAL_EXPRESSION($1, $3); }
        # { $$ = YACC_NOT_EQUAL_EXPRESSION($1, $3); }

    def p_templated_and_expression(self, p):
        """templated_and_expression : templated_equality_expression
                                    | templated_and_expression '&' templated_equality_expression
        """
        # { $$ = YACC_AND_EXPRESSION($1, $3); }

    def p_templated_exclusive_or_expression(self, p):
        """templated_exclusive_or_expression : templated_and_expression
                                             | templated_exclusive_or_expression '^' templated_and_expression
        """
        # { $$ = YACC_EXCLUSIVE_OR_EXPRESSION($1, $3); }

    def p_templated_inclusive_or_expression(self, p):
        """templated_inclusive_or_expression : templated_exclusive_or_expression
                                             | templated_inclusive_or_expression '|' templated_exclusive_or_expression
        """
        # { $$ = YACC_INCLUSIVE_OR_EXPRESSION($1, $3); }

    def p_templated_logical_and_expression(self, p):
        """templated_logical_and_expression : templated_inclusive_or_expression
                                            | templated_logical_and_expression LOG_AND templated_inclusive_or_expression
        """
        # { $$ = YACC_LOGICAL_AND_EXPRESSION($1, $3); }

    def p_templated_logical_or_expression(self, p):
        """templated_logical_or_expression : templated_logical_and_expression
                                           | templated_logical_or_expression LOG_OR templated_logical_and_expression
        """
        # { $$ = YACC_LOGICAL_OR_EXPRESSION($1, $3); }

    def p_templated_conditional_expression(self, p):
        """templated_conditional_expression : templated_logical_or_expression
                                            | templated_logical_or_expression '?' templated_expression ':' templated_assignment_expression
        """
        # { $$ = YACC_CONDITIONAL_EXPRESSION($1, $3, $5); }

    def p_templated_assignment_expression(self, p):
        """templated_assignment_expression : templated_conditional_expression
                                           | templated_logical_or_expression assignment_operator templated_assignment_expression
                                           | templated_throw_expression
        """
        # { $$ = YACC_ASSIGNMENT_EXPRESSION($1, $2, $3); }

    def p_templated_expression(self, p):
        """templated_expression : templated_assignment_expression
                                | templated_expression_list ',' templated_assignment_expression
        """
        # { $$ = YACC_EXPRESSION(YACC_EXPRESSIONS($1, $3)); }

    def p_templated_expression_list(self, p):
        """templated_expression_list : templated_assignment_expression
                                     | templated_expression_list ',' templated_assignment_expression
        """
        # { $$ = YACC_EXPRESSIONS(0, $1); }
        # { $$ = YACC_EXPRESSIONS($1, $3); }

    #--------------------------------------------------------------------------
    # A.5 Statements
    #--------------------------------------------------------------------------

    # Parsing statements is easy once simple_declaration has been generalised
    # to cover expression_statement.

    def p_looping_statement(self, p):
        """looping_statement : start_search looped_statement
        """
        # { $$ = YACC_LINED_STATEMENT($2, $1); end_search($$); }

    def p_looped_statement(self, p):
        """looped_statement : statement
                            | advance_search '+' looped_statement
                            | advance_search '-'
        """
        # { $$ = $3; }
        # { $$ = 0; }

    def p_statement(self, p):
        """statement : control_statement
                     | compound_statement
                     | declaration_statement
                     | try_block
        """
        # { $$ = YACC_TRY_BLOCK_STATEMENT($1); }

    def p_control_statement(self, p):
        """control_statement : labeled_statement
                             | selection_statement
                             | iteration_statement
                             | jump_statement
        """

    def p_labeled_statement(self, p):
        """labeled_statement : identifier ':' looping_statement
                             | CASE constant_expression ':' looping_statement
                             | DEFAULT ':' looping_statement
        """
        # { $$ = YACC_LABEL_STATEMENT($1, $3); }
        # { $$ = YACC_CASE_STATEMENT($2, $4); }
        # { $$ = YACC_DEFAULT_STATEMENT($3); }

    def p_compound_statement(self, p):
        """compound_statement : '{' statement_seq_opt '}'
                              | '{' statement_seq_opt looping_statement '#' bang error '}'
        """
        # { $$ = YACC_COMPOUND_STATEMENT($2); }
        # { $$ = $2; YACC_UNBANG($5, "Bad statement-seq."); }

    def p_statement_seq(self, p):
        """statement_seq_opt :
                             | statement_seq_opt looping_statement
                             | statement_seq_opt looping_statement '#' bang error ';'
        """
        # { $$ = YACC_STATEMENTS(0, 0); }
        # { $$ = YACC_STATEMENTS($1, YACC_COMPILE_STATEMENT($2)); }
        # { $$ = $1; YACC_UNBANG($4, "Bad statement."); }

    # The dangling else conflict is resolved to the innermost if.
    def p_selection_statement(self, p):
        """selection_statement : IF '(' condition ')' looping_statement %prec SHIFT_THERE
                               | IF '(' condition ')' looping_statement ELSE looping_statement
                               | SWITCH '(' condition ')' looping_statement
        """
        # { $$ = YACC_IF_STATEMENT($3, $5, 0); }
        # { $$ = YACC_IF_STATEMENT($3, $5, $7); }
        # { $$ = YACC_SWITCH_STATEMENT($3, $5); }

    def p_condition_1(self, p):
        """condition_opt :
                         | condition
        """
        # { $$ = YACC_CONDITION(0); }

    def p_condition_2(self, p):
        """condition : parameter_declaration_list
        """
        # { $$ = YACC_CONDITION($1); }

    def p_iteration_statement(self, p):
        """iteration_statement : WHILE '(' condition ')' looping_statement
                               | DO looping_statement WHILE '(' expression ')' ';'
                               | FOR '(' for_init_statement condition_opt ';' expression_opt ')' looping_statement
        """
        # { $$ = YACC_WHILE_STATEMENT($3, $5); }
        # { $$ = YACC_DO_WHILE_STATEMENT($2, $5); }
        # { $$ = YACC_FOR_STATEMENT($3, $4, $6, $8); }

    def p_for_init_statement(self, p):
        """for_init_statement : simple_declaration
        """

    def p_jump_statement(self, p):
        """jump_statement : BREAK ';'
                          | CONTINUE ';'
                          | RETURN expression_opt ';'
                          | GOTO identifier ';'
        """
        # { $$ = YACC_BREAK_STATEMENT(); }
        # { $$ = YACC_CONTINUE_STATEMENT(); }
        # { $$ = YACC_RETURN_STATEMENT($2); }
        # { $$ = YACC_GOTO_STATEMENT($2); }

    def p_declaration_statement(self, p):
        """declaration_statement : block_declaration
        """
        # { $$ = YACC_DECLARATION_STATEMENT($1); }

    #--------------------------------------------------------------------------
    # A.6 Declarations
    #--------------------------------------------------------------------------
    def p_compound_declaration(self, p):
        """compound_declaration : '{' nest declaration_seq_opt '}'
                                | '{' nest declaration_seq_opt util looping_declaration '#' bang error '}'
        """
        # { $$ = $3; unnest($2); }
        # { $$ = $3; unnest($2); YACC_UNBANG($7, "Bad declaration-seq."); }

    def p_declaration_seq(self, p):
        """declaration_seq_opt :
                               | declaration_seq_opt util looping_declaration
                               | declaration_seq_opt util looping_declaration '#' bang error ';'
        """
        # { $$ = YACC_DECLARATIONS(0, 0); }
        # { $$ = YACC_DECLARATIONS($1, YACC_COMPILE_DECLARATION($2, $3)); }
        # { $$ = $1; YACC_UNBANG($5, "Bad declaration."); }

    def p_looping_declaration(self, p):
        """looping_declaration : start_search1 looped_declaration
        """
        # { $$ = YACC_LINED_DECLARATION($2, $1); end_search($$); }

    def p_looped_declaration(self, p):
        """looped_declaration : declaration
                              | advance_search '+' looped_declaration
                              | advance_search '-'
        """
        # { $$ = $3; }
        # { $$ = 0; }

    def p_declaration(self, p):
        """declaration : block_declaration
                       | function_definition
                       | template_declaration
                       | explicit_specialization
                       | specialised_declaration
        """
        # { $$ = YACC_SIMPLE_DECLARATION($1); }

    def p_specialised_declaration(self, p):
        """specialised_declaration : linkage_specification
                                   | namespace_definition
                                   | TEMPLATE specialised_declaration
        """
        # { $$ = YACC_LINKAGE_SPECIFICATION($1); }
        # { $$ = YACC_NAMESPACE_DECLARATION($1); }
        # { $$ = YACC_SET_TEMPLATE_DECLARATION($2); }

    def p_block_declaration(self, p):
        """block_declaration : simple_declaration
                             | specialised_block_declaration
        """
        # { $$ = YACC_SIMPLE_DECLARATION($1); }

    def p_specialised_block_declaration(self, p):
        """specialised_block_declaration : asm_definition
                                         | namespace_alias_definition
                                         | using_declaration
                                         | using_directive
                                         | TEMPLATE specialised_block_declaration
        """
        # { $$ = YACC_SET_TEMPLATE_DECLARATION($2); }

    def p_simple_declaration(self, p):
        """simple_declaration : ';'
                              | init_declaration ';'
                              | init_declarations ';'
                              | decl_specifier_prefix simple_declaration
        """
        # { $$ = YACC_EXPRESSION(0); }
        #
        # { $$ = $1; }
        # { $$ = YACC_DECL_SPECIFIER_EXPRESSION($2, $1); }

    # A decl-specifier following a ptr_operator provokes a shift-reduce conflict for
    #
    #     * const name
    #
    # which is resolved in favour of the pointer, and implemented by providing versions
    # of decl-specifier guaranteed not to start with a cv_qualifier.
    #
    # decl-specifiers are implemented type-centrically. That is the semantic constraint
    # that there must be a type is exploited to impose structure, but actually eliminate
    # very little syntax. built-in types are multi-name and so need a different policy.
    #
    # non-type decl-specifiers are bound to the left-most type in a decl-specifier-seq,
    # by parsing from the right and attaching suffixes to the right-hand type. Finally
    # residual prefixes attach to the left.
    def p_suffix_built_in_decl_specifier_raw(self, p):
        """suffix_built_in_decl_specifier_raw : built_in_type_specifier
                                              | suffix_built_in_decl_specifier_raw built_in_type_specifier
                                              | suffix_built_in_decl_specifier_raw decl_specifier_suffix
        """
        # { $$ = $1; }
        # { $$ = YACC_BUILT_IN_NAME($1, $2); }
        # { $$ = YACC_DECL_SPECIFIER_NAME($1, $2); }

    def p_suffix_built_in_decl_specifier(self, p):
        """suffix_built_in_decl_specifier : suffix_built_in_decl_specifier_raw
                                          | TEMPLATE suffix_built_in_decl_specifier
        """
        # { $$ = $1; }
        # { $$ = YACC_SET_TEMPLATE_NAME($2); }

    def p_suffix_named_decl_specifier_1(self, p):
        """suffix_named_decl_specifier : scoped_id
                                       | elaborate_type_specifier
                                       | suffix_named_decl_specifier decl_specifier_suffix
        """
        # { $$ = $1; }
        # { $$ = $1; }
        # { $$ = YACC_DECL_SPECIFIER_NAME($1, $2); }

    def p_suffix_named_decl_specifier_2(self, p):
        """suffix_named_decl_specifier_bi : suffix_named_decl_specifier
                                          | suffix_named_decl_specifier suffix_built_in_decl_specifier_raw
        """
        # { $$ = YACC_NAME_EXPRESSION($1); }
        # { $$ = YACC_TYPED_NAME($1, $2); }

    def p_suffix_named_decl_specifiers_1(self, p):
        """suffix_named_decl_specifiers : suffix_named_decl_specifier_bi
                                        | suffix_named_decl_specifiers suffix_named_decl_specifier_bi
        """
        # { $$ = YACC_TYPED_NAME($1, $2); }

    def p_suffix_named_decl_specifiers_2(self, p):
        """suffix_named_decl_specifiers_sf : scoped_special_function_id
                                           | suffix_named_decl_specifiers
                                           | suffix_named_decl_specifiers scoped_special_function_id
        """
        # { $$ = YACC_NAME_EXPRESSION($1); }
        #
        # { $$ = YACC_TYPED_NAME($1, $2); }

    def p_suffix_decl_specified_ids(self, p):
        """suffix_decl_specified_ids : suffix_built_in_decl_specifier
                                     | suffix_built_in_decl_specifier suffix_named_decl_specifiers_sf
                                     | suffix_named_decl_specifiers_sf
        """
        # { $$ = YACC_TYPED_NAME($1, $2); }

    def p_suffix_decl_specified_scope(self, p):
        """suffix_decl_specified_scope : suffix_named_decl_specifiers SCOPE
                                       | suffix_built_in_decl_specifier suffix_named_decl_specifiers SCOPE
                                       | suffix_built_in_decl_specifier SCOPE
        """
        # { $$ = YACC_TYPED_NAME($1, $2); }
        # { $$ = YACC_NAME_EXPRESSION($1); }

    def p_decl_specifier_affix(self, p):
        """decl_specifier_affix : storage_class_specifier
                                | function_specifier
                                | FRIEND
                                | TYPEDEF
                                | cv_qualifier
        """
        # { $$ = $1; }

    def p_decl_specifier_suffix(self, p):
        """decl_specifier_suffix : decl_specifier_affix
        """

    def p_decl_specifier_prefix(self, p):
        """decl_specifier_prefix : decl_specifier_affix
                                 | TEMPLATE decl_specifier_prefix
        """
        # { $$ = YACC_SET_TEMPLATE_DECL_SPECIFIER($2); }

    def p_storage_class_specifier(self, p):
        """storage_class_specifier : REGISTER
                                   | STATIC
                                   | MUTABLE
                                   | EXTERN %prec SHIFT_THERE
                                   | AUTO
        """

    def p_function_specifier(self, p):
        """function_specifier : EXPLICIT
                              | INLINE
                              | VIRTUAL
        """

    def p_type_specifier(self, p):
        """type_specifier : simple_type_specifier
                          | elaborate_type_specifier
                          | cv_qualifier
        """
        # { $$ = YACC_CV_DECL_SPECIFIER($1); }

    def p_elaborate_type_specifier(self, p):
        """elaborate_type_specifier : class_specifier
                                    | enum_specifier
                                    | elaborated_type_specifier
                                    | TEMPLATE elaborate_type_specifier
        """
        # { $$ = YACC_SET_TEMPLATE_ID($2); }

    def p_simple_type_specifier(self, p):
        """simple_type_specifier : scoped_id
                                 | built_in_type_specifier
        """
        # { $$ = YACC_BUILT_IN_ID_ID($1); }

    def p_built_in_type_specifier(self, p):
        """built_in_type_specifier : CHAR
                                   | WCHAR_T
                                   | BOOL
                                   | SHORT
                                   | INT
                                   | LONG
                                   | SIGNED
                                   | UNSIGNED
                                   | FLOAT
                                   | DOUBLE
                                   | VOID
        """

    # The over-general use of declaration_expression to cover decl-
    # specifier-seq.opt declarator in a function-definition means that
    #
    #     class X {};
    #
    # could be a function-definition or a class-specifier.
    #
    #     enum X {};
    #
    # could be a function-definition or an enum-specifier. The function-
    # definition is not syntactically valid so resolving the false conflict
    # in favour of the elaborated_type_specifier is correct.
    def p_elaborated_type_specifier(self, p):
        """elaborated_type_specifier : elaborated_class_specifier
                                     | elaborated_enum_specifier
                                     | TYPENAME scoped_id
        """
        # { $$ = YACC_ELABORATED_TYPE_SPECIFIER($1, $2); }

    def p_elaborated_enum_specifier(self, p):
        """elaborated_enum_specifier : ENUM scoped_id %prec SHIFT_THERE
                                     | ENUM CLASS scoped_id %prec SHIFT_THERE
        """
        # { $$ = YACC_ELABORATED_TYPE_SPECIFIER($1, $2); }

    def p_enum_specifier(self, p):
        """enum_specifier : ENUM CLASS scoped_id enumerator_clause
                          | ENUM scoped_id enumerator_clause
                          | ENUM enumerator_clause
        """
        # { $$ = YACC_ENUM_SPECIFIER_ID($2, $3); }
        # { $$ = YACC_ENUM_SPECIFIER_ID(0, $2); }

    def p_enumerator_clause(self, p):
        """enumerator_clause : '{' enumerator_list_ecarb
                             | '{' enumerator_list enumerator_list_ecarb
                             | '{' enumerator_list ',' enumerator_definition_ecarb
        """
        # { $$ = YACC_ENUMERATORS(0, 0); }
        # { $$ = $2; }
        # { $$ = $2; }

    def p_enumerator_list_ecarb(self, p):
        """enumerator_list_ecarb : '}'
                                 | bang error '}'
        """
        #
        # { YACC_UNBANG($1, "Bad enumerator-list."); }

    def p_enumerator_definition_ecarb(self, p):
        """enumerator_definition_ecarb : '}'
                                       | bang error '}'
        """
        # { }
        # { YACC_UNBANG($1, "Bad enumerator-definition."); }

    def p_enumerator_definition_filler(self, p):
        """enumerator_definition_filler :
                                        | bang error ','
        """
        # { YACC_UNBANG($1, "Bad enumerator-definition."); }

    def p_enumerator_list_head(self, p):
        """enumerator_list_head : enumerator_definition_filler
                                | enumerator_list ',' enumerator_definition_filler
        """
        # { $$ = YACC_ENUMERATORS(0, 0); }

    def p_enumerator_list(self, p):
        """enumerator_list : enumerator_list_head enumerator_definition
        """
        # { $$ = YACC_ENUMERATORS($1, $2); }

    def p_enumerator_definition(self, p):
        """enumerator_definition : enumerator
                                 | enumerator '=' constant_expression
        """
        # { $$ = YACC_ENUMERATOR($1, 0); }
        # { $$ = YACC_ENUMERATOR($1, $3); }

    def p_enumerator(self, p):
        """enumerator : identifier
        """

    def p_namespace_definition(self, p):
        """namespace_definition : NAMESPACE scoped_id compound_declaration
                                | NAMESPACE compound_declaration
        """
        # { $$ = YACC_NAMESPACE_DEFINITION($2, $3); }
        # { $$ = YACC_NAMESPACE_DEFINITION(0, $2); }

    def p_namespace_alias_definition(self, p):
        """namespace_alias_definition : NAMESPACE scoped_id '=' scoped_id ';'
        """
        # { $$ = YACC_NAMESPACE_ALIAS_DEFINITION($2, $4); }

    def p_using_declaration(self, p):
        """using_declaration : USING declarator_id ';'
                             | USING TYPENAME declarator_id ';'
        """
        # { $$ = YACC_USING_DECLARATION(false, $2); }
        # { $$ = YACC_USING_DECLARATION(true, $3); }

    def p_using_directive(self, p):
        """using_directive : USING NAMESPACE scoped_id ';'
        """
        # { $$ = YACC_USING_DIRECTIVE($3); }

    def p_asm_definition(self, p):
        """asm_definition : ASM '(' string ')' ';'
        """
        # { $$ = YACC_ASM_DEFINITION($3); }

    def p_linkage_specification(self, p):
        """linkage_specification : EXTERN string looping_declaration
                                 | EXTERN string compound_declaration
        """
        # { $$ = YACC_LINKAGE_SPECIFIER($2, $3); }
        # { $$ = YACC_LINKAGE_SPECIFIER($2, $3); }

    #--------------------------------------------------------------------------
    # A.7 Declarators
    #--------------------------------------------------------------------------

    # init-declarator is named init_declaration to reflect the embedded decl-
    # specifier-seq.opt
    def p_init_declarations(self, p):
        """init_declarations : assignment_expression ',' init_declaration
                             | init_declarations ',' init_declaration
        """
        # { $$ = YACC_EXPRESSIONS(YACC_EXPRESSIONS(0, $1), $3); }
        # { $$ = YACC_EXPRESSIONS($1, $3); }

    def p_init_declaration(self, p):
        """init_declaration : assignment_expression
        """

    def p_star_ptr_operator(self, p):
        """star_ptr_operator : '*'
                             | star_ptr_operator cv_qualifier
        """
        # { $$ = YACC_POINTER_DECLARATOR(); }
        # { $$ = YACC_CV_DECLARATOR($1, $2); }

    def p_nested_ptr_operator(self, p):
        """nested_ptr_operator : star_ptr_operator
                               | id_scope nested_ptr_operator
        """
        # { $$ = $1; }
        # { $$ = YACC_NESTED_DECLARATOR($1, $2); }

    def p_ptr_operator(self, p):
        """ptr_operator : '&'
                        | nested_ptr_operator
                        | global_scope nested_ptr_operator
        """
        # { $$ = YACC_REFERENCE_DECLARATOR(); }
        # { $$ = $1; }
        # { $$ = YACC_GLOBAL_DECLARATOR($1, $2); }

    def p_ptr_operator_seq_1(self, p):
        """ptr_operator_seq : ptr_operator
                            | ptr_operator ptr_operator_seq
        """
        # { $$ = YACC_POINTER_EXPRESSION($1, 0); }
        # { $$ = YACC_POINTER_EXPRESSION($1, $2); }

    def p_ptr_operator_seq_2(self, p):
        """ptr_operator_seq_opt : %prec SHIFT_THERE
                                | ptr_operator ptr_operator_seq_opt

        """
        # { $$ = YACC_EXPRESSION(0); }
        # { $$ = YACC_POINTER_EXPRESSION($1, $2); }

    def p_cv_qualifier_seq(self, p):
        """cv_qualifier_seq_opt :
                                | cv_qualifier_seq_opt cv_qualifier
        """
        # { $$ = YACC_CV_QUALIFIERS(0, 0); }
        # { $$ = YACC_CV_QUALIFIERS($1, $2); }

    def p_cv_qualifier(self, p):
        """cv_qualifier : CONST
                        | VOLATILE
        """
        # /*type_id                                                                                       -- also covered by parameter declaration */

    def p_type_id(self, p):
        """type_id : type_specifier abstract_declarator_opt
                   | type_specifier type_id
        """
        # { $$ = YACC_TYPED_EXPRESSION($1, $2); }
        # { $$ = YACC_TYPED_EXPRESSION($1, $2); }

    def p_abstract_declarator(self, p):
        """abstract_declarator_opt :
                                   | ptr_operator abstract_declarator_opt
                                   | direct_abstract_declarator
        """
        # { $$ = 0; }
        # { $$ = YACC_POINTER_EXPRESSION($1, $2); }

    def p_direct_abstract_declarator_1(self, p):
        """direct_abstract_declarator_opt :
                                          | direct_abstract_declarator
        """
        # { $$ = 0; }

    def p_direct_abstract_declarator_2(self, p):
        """direct_abstract_declarator : direct_abstract_declarator_opt parenthesis_clause
                                      | direct_abstract_declarator_opt '[' ']'
                                      | direct_abstract_declarator_opt '[' constant_expression ']'
        """
        # { $$ = YACC_CALL_EXPRESSION($1, $2); }
        # { $$ = YACC_ARRAY_EXPRESSION($1, 0); }
        # { $$ = YACC_ARRAY_EXPRESSION($1, $3); }

        # /*  |                               '(' abstract_declarator ')'                                 -- covered by parenthesis_clause */

    def p_parenthesis_clause(self, p):
        """parenthesis_clause : parameters_clause cv_qualifier_seq_opt
                              | parameters_clause cv_qualifier_seq_opt exception_specification
        """
        # { $$ = YACC_PARENTHESISED($1, $2, 0); }
        # { $$ = YACC_PARENTHESISED($1, $2, $3); }

    def p_parameters_clause(self, p):
        """parameters_clause : '(' parameter_declaration_clause ')'"""
        # { $$ = $2; }

    def p_parameter_declaration_clause(self, p):
        """parameter_declaration_clause :
                                        | parameter_declaration_list
                                        | parameter_declaration_list ELLIPSIS
        """
        # { $$ = YACC_PARAMETERS(0, 0); }
        # { $$ = YACC_PARAMETERS($1, YACC_ELLIPSIS_EXPRESSION()); }

    def p_parameter_declaration_list(self, p):
        """parameter_declaration_list : parameter_declaration
                                      | parameter_declaration_list ',' parameter_declaration
        """
        # { $$ = YACC_PARAMETERS(0, $1); }
        # { $$ = YACC_PARAMETERS($1, $3); }

    # A typed abstract qualifier such as
    #
    #      Class * ...
    #
    # looks like a multiply, so pointers are parsed as their binary operation
    # equivalents that ultimately terminate with a degenerate right hand term.
    def p_abstract_pointer_declaration(self, p):
        """abstract_pointer_declaration : ptr_operator_seq
                                        | multiplicative_expression star_ptr_operator ptr_operator_seq_opt
        """
        # { $$ = YACC_MULTIPLY_EXPRESSION($1, $2, $3); }

    def p_abstract_parameter_declaration(self, p):
        """abstract_parameter_declaration : abstract_pointer_declaration
                                          | and_expression '&'
                                          | and_expression '&' abstract_pointer_declaration
        """
        # { $$ = YACC_LOGICAL_AND_EXPRESSION($1, 0); }
        # { $$ = YACC_LOGICAL_AND_EXPRESSION($1, $3); }

    def p_special_parameter_declaration(self, p):
        """special_parameter_declaration : abstract_parameter_declaration
                                         | abstract_parameter_declaration '=' assignment_expression
                                         | ELLIPSIS
        """
        # { $$ = YACC_ASSIGNMENT_EXPRESSION($1, $2, $3); }
        # { $$ = YACC_ELLIPSIS_EXPRESSION(); }

    def p_parameter_declaration(self, p):
        """parameter_declaration : assignment_expression
                                 | special_parameter_declaration
                                 | decl_specifier_prefix parameter_declaration
        """
        # { $$ = YACC_EXPRESSION_PARAMETER($1); }
        # { $$ = YACC_EXPRESSION_PARAMETER($1); }
        # { $$ = YACC_DECL_SPECIFIER_PARAMETER($2, $1); }

    # The grammar is repeated for use within template <>
    def p_templated_parameter_declaration(self, p):
        """templated_parameter_declaration : templated_assignment_expression
                                           | templated_abstract_declaration
                                           | templated_abstract_declaration '=' templated_assignment_expression
                                           | decl_specifier_prefix templated_parameter_declaration
        """
        # { $$ = YACC_EXPRESSION_PARAMETER(YACC_ASSIGNMENT_EXPRESSION($1, $2, $3)); }
        # { $$ = YACC_EXPRESSION_PARAMETER($1); }
        # { $$ = YACC_EXPRESSION_PARAMETER($1); }
        # { $$ = YACC_DECL_SPECIFIER_PARAMETER($2, $1); }

    def p_templated_abstract_declaration(self, p):
        """templated_abstract_declaration : abstract_pointer_declaration
                                          | templated_and_expression '&'
                                          | templated_and_expression '&' abstract_pointer_declaration
        """
        # { $$ = YACC_LOGICAL_AND_EXPRESSION($1, 0); }
        # { $$ = YACC_LOGICAL_AND_EXPRESSION($1, $3); }

    # function_definition includes constructor, destructor, implicit int
    # definitions too. A local destructor is successfully parsed as a
    # function-declaration but the ~ was treated as a unary operator.
    # constructor_head is the prefix ambiguity between a constructor and a
    # member-init-list starting with a bit-field.
    def p_function_definition(self, p):
        """function_definition : ctor_definition
                               | func_definition
        """

    def p_func_definition(self, p):
        """func_definition : assignment_expression function_try_block
                           | assignment_expression function_body
                           | decl_specifier_prefix func_definition
        """
        # { $$ = YACC_FUNCTION_DEFINITION($1, $2); }
        # { $$ = YACC_FUNCTION_DEFINITION($1, $2); }
        # { $$ = YACC_DECL_SPECIFIER_EXPRESSION($2, $1); }

    def p_ctor_definition(self, p):
        """ctor_definition : constructor_head function_try_block
                           | constructor_head function_body
                           | decl_specifier_prefix ctor_definition
        """
        # { $$ = YACC_FUNCTION_DEFINITION($1, $2); }
        # { $$ = YACC_FUNCTION_DEFINITION($1, $2); }
        # { $$ = YACC_DECL_SPECIFIER_EXPRESSION($2, $1); }

    def p_constructor_head(self, p):
        """constructor_head : bit_field_init_declaration
                            | constructor_head ',' assignment_expression
        """
        # { $$ = YACC_EXPRESSIONS(0, $1); }
        # { $$ = YACC_EXPRESSIONS($1, $3); }

    def p_function_try_block(self, p):
        """function_try_block : TRY function_block handler_seq
        """
        # { $$ = YACC_TRY_FUNCTION_BLOCK($2, $3); }

    def p_function_block(self, p):
        """function_block : ctor_initializer_opt function_body
        """
        # { $$ = YACC_CTOR_FUNCTION_BLOCK($2, $1); }

    def p_function_body(self, p):
        """function_body : compound_statement
        """
        # { $$ = YACC_FUNCTION_BLOCK($1); }

    # An = initializer looks like an extended assignment_expression.
    # An () initializer looks like a function call.
    # initializer is therefore flattened into its generalised customers.
    def p_initializer_clause(self, p):
        """initializer_clause : assignment_expression
                              | braced_initializer
        """
        # { $$ = YACC_INITIALIZER_EXPRESSION_CLAUSE($1); }

    def p_braced_initializer(self, p):
        """braced_initializer : '{' initializer_list '}'
                              | '{' initializer_list ',' '}'
                              | '{' '}'
                              | '{' looping_initializer_clause '#' bang error '}'
                              | '{' initializer_list ',' looping_initializer_clause '#' bang error '}'
        """
        # { $$ = YACC_INITIALIZER_LIST_CLAUSE($2); }
        # { $$ = YACC_INITIALIZER_LIST_CLAUSE($2); }
        # { $$ = YACC_INITIALIZER_LIST_CLAUSE(0); }
        # { $$ = 0; YACC_UNBANG($4, "Bad initializer_clause."); }
        # { $$ = $2; YACC_UNBANG($6, "Bad initializer_clause."); }

    def p_initializer_list(self, p):
        """initializer_list : looping_initializer_clause
                            | initializer_list ',' looping_initializer_clause
        """
        # { $$ = YACC_INITIALIZER_CLAUSES(0, $1); }
        # { $$ = YACC_INITIALIZER_CLAUSES($1, $3); }

    def p_looping_initializer_clause(self, p):
        """looping_initializer_clause : start_search looped_initializer_clause
        """
        # { $$ = $2; end_search($$); }

    def p_looped_initializer_clause(self, p):
        """looped_initializer_clause : initializer_clause
                                     | advance_search '+' looped_initializer_clause
                                     | advance_search '-'
        """
        # { $$ = $3; }
        # { $$ = 0; }

    #--------------------------------------------------------------------------
    # A.8 Classes
    #--------------------------------------------------------------------------
    #
    # An anonymous bit-field declaration may look very like inheritance:
    #
    #     const int B = 3;
    #     class A : B ;
    #
    # The two usages are too distant to try to create and enforce a common
    # prefix so we have to resort to a parser hack by backtracking. Inheritance
    # is much the most likely so we mark the input stream context and try to
    # parse a base-clause. If we successfully reach a { the base-clause is ok
    # and inheritance was the correct choice so we unmark and continue. If we
    # fail to find the { an error token causes back-tracking to the alternative
    # parse in elaborated_type_specifier which regenerates the : and declares
    # unconditional success.

    def p_colon_mark(self, p):
        """colon_mark : ':'
        """
        # { $$ = mark(); }

    def p_elaborated_class_specifier(self, p):
        """elaborated_class_specifier : class_key scoped_id %prec SHIFT_THERE
                                      | class_key scoped_id colon_mark error
        """
        # { $$ = YACC_ELABORATED_TYPE_SPECIFIER($1, $2); }
        # { $$ = YACC_ELABORATED_TYPE_SPECIFIER($1, $2); rewind_colon($3); }

    def p_class_specifier_head(self, p):
        """class_specifier_head : class_key scoped_id colon_mark base_specifier_list '{'
                                | class_key ':' base_specifier_list '{'
                                | class_key scoped_id '{'
                                | class_key '{'
        """
        # { unmark($4); $$ = YACC_CLASS_SPECIFIER_ID($1, $2, $4); }
        # { $$ = YACC_CLASS_SPECIFIER_ID($1, 0, $3); }
        # { $$ = YACC_CLASS_SPECIFIER_ID($1, $2, 0); }
        # { $$ = YACC_CLASS_SPECIFIER_ID($1, 0, 0); }

    def p_class_key(self, p):
        """class_key : CLASS
                     | STRUCT
                     | UNION
        """

    def p_class_specifier(self, p):
        """class_specifier : class_specifier_head member_specification_opt '}'
                           | class_specifier_head member_specification_opt util looping_member_declaration '#' bang error '}'
        """
        # { $$ = YACC_CLASS_MEMBERS($1, $2); }
        # { $$ = YACC_CLASS_MEMBERS($1, $2); YACC_UNBANG($6, "Bad member_specification_opt."); }

    def p_member_specification(self, p):
        """member_specification_opt :
                                    | member_specification_opt util looping_member_declaration
                                    | member_specification_opt util looping_member_declaration '#' bang error ';'
        """
        # { $$ = YACC_MEMBER_DECLARATIONS(0, 0); }
        # { $$ = YACC_MEMBER_DECLARATIONS($1, YACC_COMPILE_DECLARATION($2, $3)); }
        # { $$ = $1; YACC_UNBANG($5, "Bad member-declaration."); }

    def p_looping_member_declaration(self, p):
        """looping_member_declaration : start_search looped_member_declaration
        """
        # { $$ = YACC_LINED_DECLARATION($2, $1); end_search($$); }

    def p_looped_member_declaration(self, p):
        """looped_member_declaration : member_declaration
                                     | advance_search '+' looped_member_declaration
                                     | advance_search '-'
        """
        # { $$ = $3; }
        # { $$ = 0; }

    def p_member_declaration(self, p):
        """member_declaration : accessibility_specifier
                              | simple_member_declaration
                              | function_definition
                              | using_declaration
                              | template_declaration
        """
        # { $$ = YACC_SIMPLE_DECLARATION($1); }
        # { $$ = YACC_SIMPLE_DECLARATION($1); }

        # /*  |                               function_definition ';'                                     -- trailing ; covered by null declaration */
        # /*  |                               qualified_id ';'                                            -- covered by simple_member_declaration */

    # The generality of constructor names (there need be no parenthesised argument list) means that that
    #         name : f(g), h(i)
    # could be the start of a constructor or the start of an anonymous bit-field. An ambiguity is avoided by
    # parsing the ctor-initializer of a function_definition as a bit-field.
    def p_simple_member_declaration(self, p):
        """simple_member_declaration : ';'
                                     | assignment_expression ';'
                                     | constructor_head ';'
                                     | member_init_declarations ';'
                                     | decl_specifier_prefix simple_member_declaration
        """
        # { $$ = YACC_EXPRESSION(0); }
        # { $$ = $1; }
        # { $$ = $1; }
        # { $$ = YACC_DECL_SPECIFIER_EXPRESSION($2, $1); }

    def p_member_init_declarations(self, p):
        """member_init_declarations : assignment_expression ',' member_init_declaration
                                    | constructor_head ',' bit_field_init_declaration
                                    | member_init_declarations ',' member_init_declaration
        """
        # { $$ = YACC_EXPRESSIONS(YACC_EXPRESSIONS(0, $1), $3); }
        # { $$ = YACC_EXPRESSIONS($1, $3); }
        # { $$ = YACC_EXPRESSIONS($1, $3); }

    def p_member_init_declaration(self, p):
        """member_init_declaration : assignment_expression
                                   | bit_field_init_declaration
        """

    def p_accessibility_specifier(self, p):
        """accessibility_specifier : access_specifier ':'
        """
        # { $$ = YACC_ACCESSIBILITY_DECLARATION($1); }

    def p_bit_field_declaration(self, p):
        """bit_field_declaration : assignment_expression ':' bit_field_width
                                 | ':' bit_field_width
        """
        # { $$ = YACC_BIT_FIELD_EXPRESSION($1, $3); }
        # { $$ = YACC_BIT_FIELD_EXPRESSION(0, $2); }

    def p_bit_field_width(self, p):
        """bit_field_width : logical_or_expression
                           | logical_or_expression '?' bit_field_width ':' bit_field_width
        """
        # { $$ = YACC_CONDITIONAL_EXPRESSION($1, $3, $5); }

    def p_bit_field_init_declaration(self, p):
        """bit_field_init_declaration : bit_field_declaration
                                      | bit_field_declaration '=' initializer_clause
        """
        # { $$ = YACC_ASSIGNMENT_EXPRESSION($1, $2, $3); }

    #--------------------------------------------------------------------------
    # A.9 Derived classes
    #--------------------------------------------------------------------------
    def p_base_specifier_list(self, p):
        """base_specifier_list : base_specifier
                               | base_specifier_list ',' base_specifier
        """
        # { $$ = YACC_BASE_SPECIFIERS(0, $1); }
        # { $$ = YACC_BASE_SPECIFIERS($1, $3); }

    def p_base_specifier(self, p):
        """base_specifier : scoped_id
                          | access_specifier base_specifier
                          | VIRTUAL base_specifier
        """
        # { $$ = YACC_BASE_SPECIFIER($1); }
        # { $$ = YACC_ACCESS_BASE_SPECIFIER($2, $1); }
        # { $$ = YACC_VIRTUAL_BASE_SPECIFIER($2); }

    def p_access_specifier(self, p):
        """access_specifier : PRIVATE
                            | PROTECTED
                            | PUBLIC
        """

    #--------------------------------------------------------------------------
    # A.10 Special member functions
    #--------------------------------------------------------------------------

    def p_conversion_function_id(self, p):
        """conversion_function_id : OPERATOR conversion_type_id
        """
        # { $$ = YACC_CONVERSION_FUNCTION_ID($2); }

    def p_conversion_type_id(self, p):
        """conversion_type_id : type_specifier ptr_operator_seq_opt
                              | type_specifier conversion_type_id
        """
        # { $$ = YACC_TYPED_EXPRESSION($1, $2); }
        # { $$ = YACC_TYPED_EXPRESSION($1, $2); }

    # Ctor-initialisers can look like a bit field declaration, given the generalisation of names:
    #     Class(Type) : m1(1), m2(2) {}
    #     NonClass(bit_field) : int(2), second_variable, ...
    # The grammar below is used within a function_try_block or function_definition.
    # See simple_member_declaration for use in normal member function_definition.
    def p_ctor_initializer_1(self, p):
        """ctor_initializer_opt :
                                | ctor_initializer
        """
        # { $$ = YACC_MEM_INITIALIZERS(0, 0); }

    def p_ctor_initializer_2(self, p):
        """ctor_initializer : ':' mem_initializer_list
                            | ':' mem_initializer_list bang error
        """
        # { $$ = $2; }
        # { $$ = $2; YACC_UNBANG($3, "Bad ctor-initializer."); }

    def p_mem_initializer_list(self, p):
        """mem_initializer_list : mem_initializer
                                | mem_initializer_list_head mem_initializer
        """
        # { $$ = YACC_MEM_INITIALIZERS(0, $1); }
        # { $$ = YACC_MEM_INITIALIZERS($1, $2); }

    def p_mem_initializer_list_head(self, p):
        """mem_initializer_list_head : mem_initializer_list ','
                                     | mem_initializer_list bang error ','
        """
        # { YACC_UNBANG($2, "Bad mem-initializer."); }

    def p_mem_initializer(self, p):
        """mem_initializer : mem_initializer_id '(' expression_list_opt ')'
        """
        # { $$ = YACC_MEM_INITIALIZER($1, $3); }

    def p_mem_initializer_id(self, p):
        """mem_initializer_id : scoped_id
        """

    #--------------------------------------------------------------------------
    # A.11 Overloading
    #--------------------------------------------------------------------------

    def p_operator_function_id(self, p):
        """operator_function_id : OPERATOR operator
        """
        # { $$ = YACC_OPERATOR_FUNCTION_ID($2); }

    # It is not clear from the ANSI standard whether spaces are permitted in
    # delete[]. If not then it can be recognised and returned as
    # DELETE_ARRAY by the lexer. Assuming spaces are permitted there is an
    # ambiguity created by the over generalised nature of expressions.
    # operator new is a valid delarator-id which we may have an
    # undimensioned array of. Semantic rubbish, but syntactically valid.
    # Since the array form is covered by the declarator consideration we can
    # exclude the operator here. The need for a semantic rescue can be
    # eliminated at the expense of a couple of shift-reduce conflicts by
    # removing the comments on the next four lines.
    def p_operator(self, p):
        """operator : NEW
                    | DELETE
                    | '+'
                    | '-'
                    | '*'
                    | '/'
                    | '%'
                    | '^'
                    | '&'
                    | '|'
                    | '~'
                    | '!'
                    | '='
                    | '<'
                    | '>'
                    | ASS_ADD
                    | ASS_SUB
                    | ASS_MUL
                    | ASS_DIV
                    | ASS_MOD
                    | ASS_XOR
                    | ASS_AND
                    | ASS_OR
                    | SHL
                    | SHR
                    | ASS_SHR
                    | ASS_SHL
                    | EQ
                    | NE
                    | LE
                    | GE
                    | LOG_AND
                    | LOG_OR
                    | INC
                    | DEC
                    | ','
                    | ARROW_STAR
                    | ARROW
                    | '(' ')'
                    | '[' ']'
        """
        # { $$ = YACC_OPERATOR_NEW_ID(); }
        # { $$ = YACC_OPERATOR_DELETE_ID(); }
        # { $$ = YACC_OPERATOR_ADD_ID(); }
        # { $$ = YACC_OPERATOR_SUB_ID(); }
        # { $$ = YACC_OPERATOR_MUL_ID(); }
        # { $$ = YACC_OPERATOR_DIV_ID(); }
        # { $$ = YACC_OPERATOR_MOD_ID(); }
        # { $$ = YACC_OPERATOR_XOR_ID(); }
        # { $$ = YACC_OPERATOR_BIT_AND_ID(); }
        # { $$ = YACC_OPERATOR_BIT_OR_ID(); }
        # { $$ = YACC_OPERATOR_BIT_NOT_ID(); }
        # { $$ = YACC_OPERATOR_LOG_NOT_ID(); }
        # { $$ = YACC_OPERATOR_ASS_ID(); }
        # { $$ = YACC_OPERATOR_LT_ID(); }
        # { $$ = YACC_OPERATOR_GT_ID(); }
        # { $$ = YACC_OPERATOR_ASS_ADD_ID(); }
        # { $$ = YACC_OPERATOR_ASS_SUB_ID(); }
        # { $$ = YACC_OPERATOR_ASS_MUL_ID(); }
        # { $$ = YACC_OPERATOR_ASS_DIV_ID(); }
        # { $$ = YACC_OPERATOR_ASS_MOD_ID(); }
        # { $$ = YACC_OPERATOR_ASS_XOR_ID(); }
        # { $$ = YACC_OPERATOR_ASS_BIT_AND_ID(); }
        # { $$ = YACC_OPERATOR_ASS_BIT_OR_ID(); }
        # { $$ = YACC_OPERATOR_SHL_ID(); }
        # { $$ = YACC_OPERATOR_SHR_ID(); }
        # { $$ = YACC_OPERATOR_ASS_SHR_ID(); }
        # { $$ = YACC_OPERATOR_ASS_SHL_ID(); }
        # { $$ = YACC_OPERATOR_EQ_ID(); }
        # { $$ = YACC_OPERATOR_NE_ID(); }
        # { $$ = YACC_OPERATOR_LE_ID(); }
        # { $$ = YACC_OPERATOR_GE_ID(); }
        # { $$ = YACC_OPERATOR_LOG_AND_ID(); }
        # { $$ = YACC_OPERATOR_LOG_OR_ID(); }
        # { $$ = YACC_OPERATOR_INC_ID(); }
        # { $$ = YACC_OPERATOR_DEC_ID(); }
        # { $$ = YACC_OPERATOR_COMMA_ID(); }
        # { $$ = YACC_OPERATOR_ARROW_STAR_ID(); }
        # { $$ = YACC_OPERATOR_ARROW_ID(); }
        # { $$ = YACC_OPERATOR_CALL_ID(); }
        # { $$ = YACC_OPERATOR_INDEX_ID(); }

    #--------------------------------------------------------------------------
    # A.12 Templates
    #--------------------------------------------------------------------------

    def p_template_declaration(self, p):
        """template_declaration : template_parameter_clause declaration
                                | EXPORT template_declaration
        """
        # { $$ = YACC_TEMPLATE_DECLARATION($1, $2); }
        # { $$ = YACC_DECL_SPECIFIER_DECLARATION($2, $1); }

    def p_template_parameter_clause(self, p):
        """template_parameter_clause : TEMPLATE '<' template_parameter_list '>'
        """
        # { $$ = $3; }

    def p_template_parameter_list(self, p):
        """template_parameter_list : template_parameter
                                   | template_parameter_list ',' template_parameter
        """
        # { $$ = YACC_TEMPLATE_PARAMETERS(0, $1); }
        # { $$ = YACC_TEMPLATE_PARAMETERS($1, $3); }

    def p_template_parameter(self, p):
        """template_parameter : simple_type_parameter
                              | simple_type_parameter '=' type_id
                              | templated_type_parameter
                              | templated_type_parameter '=' identifier
                              | templated_parameter_declaration
                              | bang error
        """
        # { $$ = YACC_TYPE_TEMPLATE_PARAMETER($1, 0); }
        # { $$ = YACC_TYPE_TEMPLATE_PARAMETER($1, $3); }
        # { $$ = YACC_TEMPLATED_TEMPLATE_PARAMETER($1, 0); }
        # { $$ = YACC_TEMPLATED_TEMPLATE_PARAMETER($1, $3); }
        # { $$ = YACC_TEMPLATE_PARAMETER($1); }
        # { $$ = 0; YACC_UNBANG($1, "Bad template-parameter."); }

    def p_simple_type_parameter(self, p):
        """simple_type_parameter : CLASS
                                 | TYPENAME
        """
        # { $$ = YACC_CLASS_TEMPLATE_PARAMETER(0); }
        # { $$ = YACC_TYPENAME_TEMPLATE_PARAMETER(0); }

    def p_templated_type_parameter(self, p):
        """templated_type_parameter : template_parameter_clause CLASS
                                    | template_parameter_clause CLASS identifier
        """
        # { $$ = YACC_TEMPLATED_TYPE_PARAMETER($1, 0); }
        # { $$ = YACC_TEMPLATED_TYPE_PARAMETER($1, $3); }

    def p_template_id(self, p):
        """template_id : TEMPLATE identifier '<' template_argument_list '>'
                       | TEMPLATE template_id
        """
        # { $$ = YACC_TEMPLATE_NAME($2, $4); }
        # { $$ = $2; }

    # template-argument is evaluated using a templated...expression so that >
    # resolves to end of template.
    def p_template_argument_list(self, p):
        """template_argument_list : template_argument
                                  | template_argument_list ',' template_argument
        """
        # { $$ = YACC_TEMPLATE_ARGUMENTS(0, $1); }
        # { $$ = YACC_TEMPLATE_ARGUMENTS($1, $3); }

    def p_template_argument(self, p):
        """template_argument : templated_parameter_declaration
        """
        # { $$ = YACC_TEMPLATE_ARGUMENT($1); }

    # Generalised naming makes identifier a valid declaration, so TEMPLATE
    # identifier is too. The TEMPLATE prefix is therefore folded into all
    # names, parenthesis_clause and decl_specifier_prefix.
    def p_explicit_specialization(self, p):
        """explicit_specialization : TEMPLATE '<' '>' declaration
        """
        # { $$ = YACC_EXPLICIT_SPECIALIZATION($4); }

    #--------------------------------------------------------------------------
    # A.13 Exception Handling
    #--------------------------------------------------------------------------

    def p_try_block(self, p):
        """try_block : TRY compound_statement handler_seq
        """
        # { $$ = YACC_TRY_BLOCK($2, $3); }

    def p_handler_seq(self, p):
        """handler_seq : handler
                       | handler handler_seq
        """
        # { $$ = YACC_HANDLERS(0, $1); }
        # { $$ = YACC_HANDLERS($2, $1); }

    def p_handler(self, p):
        """handler : CATCH '(' exception_declaration ')' compound_statement
        """
        # { $$ = YACC_HANDLER($3, $5); }

    def p_exception_declaration(self, p):
        """exception_declaration : parameter_declaration
        """
        # { $$ = YACC_EXCEPTION_DECLARATION($1); }

    def p_throw_expression(self, p):
        """throw_expression : THROW
                            | THROW assignment_expression
        """
        # { $$ = YACC_THROW_EXPRESSION(0); }
        # { $$ = YACC_THROW_EXPRESSION($2); }

    def p_templated_throw_expression(self, p):
        """templated_throw_expression : THROW
                                      | THROW templated_assignment_expression
        """
        # { $$ = YACC_THROW_EXPRESSION(0); }
        # { $$ = YACC_THROW_EXPRESSION($2); }

    def p_exception_specification(self, p):
        """exception_specification : THROW '(' ')'
                                   | THROW '(' type_id_list ')'
        """
        # { $$ = YACC_EXCEPTION_SPECIFICATION(0); }
        # { $$ = YACC_EXCEPTION_SPECIFICATION($3); }

    def p_type_id_list(self, p):
        """type_id_list : type_id
                        | type_id_list ',' type_id
        """
        # { $$ = YACC_EXPRESSIONS(0, $1); }
        # { $$ = YACC_EXPRESSIONS($1, $3); }

    #--------------------------------------------------------------------------
    # Back-tracking and context support
    #--------------------------------------------------------------------------

    def p_advance_search(self, p):
        """advance_search : error
        """
        # /* Rewind and queue '+' or '-' '#' */
        # { yyerrok; yyclearin; advance_search(); }

    def p_bang(self, p):
        """bang :
        """
        # /* set flag to suppress "parse error" */
        # { $$ = YACC_BANG(); }

    def p_mark(self, p):
        """mark :
        """
        # /* Push lookahead and input token stream context onto a stack */
        # { $$ = mark(); }

    def p_nest(self, p):
        """nest :
        """
        # /* Push a declaration nesting depth onto the parse stack */
        # { $$ = nest(); }

    def p_start_search(self, p):
        """start_search :
        """
        # /* Create/reset binary search context */
        # { $$ = YACC_LINE(); start_search(false); }

    def p_start_search1(self, p):
        """start_search1 :
        """
        # /* Create/reset binary search context */
        # { $$ = YACC_LINE(); start_search(true); }

    def p_util(self, p):
        """util :
        """
        # /* Get current utility mode */
        # { $$ = YACC_UTILITY_MODE(); }

    # def p_empty(self, p):
    #     'empty : '
    #     p[0] = None

    def p_error(self, p):
        # If error recovery is added here in the future, make sure
        # _get_yacc_lookahead_token still works!
        #
        if p:
            self._parse_error(
                'before: %s' % p.value,
                self._coord(
                    lineno=p.lineno,
                    column=self.clex.find_tok_column(p)
                )
            )
        else:
            self._parse_error('At end of input', '')


#------------------------------------------------------------------------------
if __name__ == "__main__":
    # import pprint
    # import time, sys

    #t1 = time.time()
    #parser = CParser(lex_optimize=True, yacc_debug=True, yacc_optimize=False)
    #sys.write(time.time() - t1)

    #buf = '''
        #int (*k)(int);
    #'''

    ## set debuglevel to 2 for debugging
    #t = parser.parse(buf, 'x.c', debuglevel=0)
    #t.show(showcoord=True)
    from seasnake.preprocessor import preprocess
    import os

    with open(sys.argv[1]) as data:
        preprocessed = preprocess(
            data.read(),
            filename=sys.argv[1],
            defines={
                'ENABLE(ATTACHMENT_ELEMENT)': '0',
                'ENABLE(CSS_GRID_LAYOUT)': '0',
                'ENABLE(DASHBOARD_SUPPORT)': '0',
                'ENABLE(DETAILS_ELEMENT)': '0',
                'ENABLE(FULLSCREEN_API)': '0',
                'ENABLE(IOS_TEXT_AUTOSIZING)': '0',
                'ENABLE(MATHML)': '0',
                'ENABLE(METER_ELEMENT)': '0',
                'ENABLE(TREE_DEBUGGING)': '1',
                'PLATFORM(IOS)': '1',
            })

        with open(os.path.splitext(os.path.basename(sys.argv[1]))[0] + ".cpp", 'w') as out:
            out.write(preprocessed)

        parser = CppParser()
        parser.parse(preprocessed, debuglevel=10)
