import re

from ply import lex
from ply.lex import TOKEN


class CppLexer(object):
    """A lexer for the C++ language.

    After building it, set the
    input text with input(), and call token() to get new
    tokens.

    The public attribute filename can be set to an initial
    filaneme, but the lexer will update it upon #line
    directives.
    """
    def __init__(self, error_func, on_lbrace_func, on_rbrace_func,
                 type_lookup_func):
        """ Create a new Lexer.

        error_func:
            An error function. Will be called with an error
            message, line and column as arguments, in case of
            an error during lexing.
        on_lbrace_func, on_rbrace_func:
            Called when an LBRACE or RBRACE is encountered
            (likely to push/pop type_lookup_func's scope)
        type_lookup_func:
            A type lookup function. Given a string, it must
            return True IFF this string is a name of a type
            that was defined with a typedef earlier.
        """
        self.error_func = error_func
        self.on_lbrace_func = on_lbrace_func
        self.on_rbrace_func = on_rbrace_func
        self.type_lookup_func = type_lookup_func
        self.filename = ''

        # Keeps track of the last token returned from self.token()
        self.last_token = None

        # Allow either "# line" or "# <num>" to support GCC's
        # cpp output
        #
        self.line_pattern = re.compile('([ \t]*line\W)|([ \t]*\d+)')
        self.pragma_pattern = re.compile('[ \t]*pragma\W')

    def build(self, **kwargs):
        """ Builds the lexer from the specification. Must be
            called after the lexer object is created.
            This method exists separately, because the PLY
            manual warns against calling lex.lex inside
            __init__
        """
        self.lexer = lex.lex(object=self, **kwargs)

    def reset_lineno(self):
        """ Resets the internal line number counter of the lexer.
        """
        self.lexer.lineno = 1

    def input(self, text):
        self.lexer.input(text)

    def token(self):
        self.last_token = self.lexer.token()
        return self.last_token

    def find_tok_column(self, token):
        """ Find the column of the token in its line.
        """
        last_cr = self.lexer.lexdata.rfind('\n', 0, token.lexpos)
        return token.lexpos - last_cr

    ######################--   PRIVATE   --######################

    ##
    ## Internal auxiliary methods
    ##
    def _error(self, msg, token):
        location = self._make_tok_location(token)
        self.error_func(msg, location[0], location[1])
        self.lexer.skip(1)

    def _make_tok_location(self, token):
        return (token.lineno, self.find_tok_column(token))

    ##
    ## Character literals
    ##
    literals = [
        '+', '-', '*', '/', '%',
        '^', '&', '|', '~', '!',
        '<',  '>',
        '=',
        ':',
        '[', ']',
        '{', '}',
        '(', ')',
        '?',
        '.',
        '\'', '\"',
        '\\',
        '@',
        '$',
        ';',
        ','
    ]

    ##
    ## Reserved keywords
    ##
    keywords = (
        "ASM", "AUTO", "BOOL", "BREAK", "CASE", "CATCH", "CHAR", "CLASS",
        "CONST", "CONST_CAST", "CONTINUE", "DEFAULT", "DELETE", "DO",
        "DOUBLE", "DYNAMIC_CAST", "ELSE", "ENUM", "EXPLICIT", "EXPORT",
        "EXTERN", "FALSE", "FLOAT", "FOR", "FRIEND", "GOTO", "IF", "INLINE",
        "INT", "LONG", "MUTABLE", "NAMESPACE", "NEW", "OPERATOR", "PRIVATE",
        "PROTECTED", "PUBLIC", "REGISTER", "REINTERPRET_CAST", "RETURN",
        "SHORT", "SIGNED", "SIZEOF", "STATIC", "STATIC_CAST", "STRUCT",
        "SWITCH", "TEMPLATE", "THIS", "THROW", "TRUE", "TRY", "TYPEDEF",
        "TYPEID", "TYPENAME", "UNION", "UNSIGNED", "USING", "VIRTUAL",
        "VOID", "VOLATILE", "WCHAR_T", "WHILE",
    )

    keyword_map = {}
    for keyword in keywords:
        keyword_map[keyword.lower()] = keyword

    ##
    ## All the tokens recognized by the lexer
    ##
    tokens = keywords + (

        # constants
        'CHARACTER_LITERAL',
        'STRING_LITERAL',
        'INTEGER_LITERAL',
        'FLOAT_LITERAL',

        'SCOPE',
        'ELLIPSIS',
        'SHL', 'SHR',
        'EQ', 'NE',
        'LE', 'GE',
        'LOG_AND', 'LOG_OR',
        'INC', 'DEC',
        'ARROW_STAR',
        'ARROW',
        'DOT_STAR',

        'ASS_ADD', 'ASS_SUB',
        'ASS_MUL', 'ASS_DIV',
        'ASS_MOD',
        'ASS_XOR',
        'ASS_AND', 'ASS_OR',
        'ASS_SHL', 'ASS_SHR',

        # pre-processor
        # 'PP_NUMBER',       # '#'

        # Identifiers
        'IDENTIFIER',

        # 'ESCAPE_SEQUENCE',
        # 'UNIVERSAL_CHARACTER_NAME',
    )

    ##
    ## Regexes for use in tokens
    ##
    ##
    ws = '[ \f\v\t]'

    digit = '[0-9]'
    hex = '[0-9A-Fa-f]'
    letter = '[A-Z_a-z]'
    simple_escape_sequence = r'(\\\'|\\\"|\\\?|\\\\|\\a|\\b|\\f|\\n|\\r|\\t|\\v)'
    octal_escape_sequence = r'(\\[0-7]|\\[0-7][0-7]|\\[0-7][0-7][0-7])'
    hexadecimal_escape_sequence = r'(\\x' + hex + '+)'
    escape_sequence = r'(' + simple_escape_sequence + '|' + octal_escape_sequence + '|' + hexadecimal_escape_sequence + ')'
    universal_character_name = r'(\\u' + hex + hex + hex + hex + r'|\\U' + hex + hex + hex + hex + hex + hex + hex + hex + ')'
    non_digit = '(' + letter + '|' + universal_character_name + ')'
    identifier = '(' + non_digit + '(' + non_digit + '|' + digit + ')*)'

    character_lit = r'(L?\'([^\'\\\n]|\\.)*)'
    character_literal = '(' + character_lit + '\')'

    string_lit = r'(L?\"([^\"\\\n]|\\.)*)'
    string_literal = r'(' + string_lit + '\")'

    integer_suffix_opt = r'(([uU]ll)|([uU]LL)|(ll[uU]?)|(LL[uU]?)|([uU][lL])|([lL][uU]?)|[uU])?'

    bin_prefix = '0[bB]'
    bin_digits = '[01]+'
    bin_literal = bin_prefix + bin_digits + integer_suffix_opt

    decimal_literal = '(0'+integer_suffix_opt+')|([1-9][0-9]*'+integer_suffix_opt+')'

    octal_literal = '0[0-7]*'+integer_suffix_opt

    hex_prefix = '0[xX]'
    hex_digits = '[0-9a-fA-F]+'
    hex_literal = hex_prefix + hex_digits + integer_suffix_opt

    integer_literal = '(' + decimal_literal + '|' + octal_literal + '|' + hex_literal + ')'

    exponent_part = r"""([eE][-+]?[0-9]+)"""
    fractional_literal = r"""([0-9]*\.[0-9]+)|([0-9]+\.)"""
    float_literal = '((((' + fractional_literal + ')' + exponent_part + '?)|([0-9]+' + exponent_part + '))[FfLl]?)'

    pp_number = r'(\.?' + digit + r'(' + digit + r'|' + non_digit + r'|[eE][-+]|\.)*)'

    ##
    ## Rules for the normal state
    ##

    # Operators
    t_SCOPE = r'::'
    t_ELLIPSIS = r'\.\.\.'

    t_SHL = r'<<'
    t_SHR = r'>>'
    t_EQ = r'=='
    t_NE = r'!='
    t_LE = r'<='
    t_GE = r'>='
    t_LOG_AND = r'&&'
    t_LOG_OR = r'\|\|'
    t_INC = r'\+\+'
    t_DEC = r'--'
    t_ARROW_STAR = r'->\*'
    t_ARROW = r'->'
    t_DOT_STAR = r'\.\*'
    t_ASS_ADD = r'\+='
    t_ASS_SUB = r'-='
    t_ASS_MUL = r'\*='
    t_ASS_DIV = r'/='
    t_ASS_MOD = r'%='
    t_ASS_XOR = r'\^='
    t_ASS_AND = r'&='
    t_ASS_OR = r'\|='
    t_ASS_SHR = r'>>='
    t_ASS_SHL = r'<<='

    # t_PP_NUMBER = pp_number

    @TOKEN(identifier)
    def t_IDENTIFIER(self, t):
        t.type = self.keyword_map.get(t.value, "IDENTIFIER")
        # if t.type == 'IDENTIFIER' and self.type_lookup_func(t.value):
        #     t.type = "TYPEID"
        return t

    # t_ESCAPE_SEQUENCE = escape_sequence

    # t_UNIVERSAL_CHARACTER_NAME = universal_character_name

    t_CHARACTER_LITERAL = character_literal
    t_STRING_LITERAL = string_literal

    t_FLOAT_LITERAL = float_literal
    t_INTEGER_LITERAL = integer_literal

    t_ignore = ' \t'

    # Newlines
    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")

    def t_error(self, t):
        msg = 'Illegal character %s' % repr(t.value[0])
        self._error(msg, t)
