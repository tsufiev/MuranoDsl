import yaql
import yaql.exceptions
import re
import types

class YaqlExpression(object):
    def __init__(self, expression):
        self._expression = str(expression)
        self._parsed_expression = yaql.parse(self._expression)

    def expression(self):
        return self._expression

    def __repr__(self):
        return 'YAQL(%s)' % self._expression

    def __str__(self):
        return self._expression

    @staticmethod
    def match(expr):
        if not isinstance(expr, types.StringTypes):
            return False
        if re.match('^[\s\w\d.:]*$', expr):
            return False
        try:
            yaql.parse(expr)
            return True
        except yaql.exceptions.YaqlGrammarException:
            return False
        except yaql.exceptions.YaqlLexicalException:
            return False

    def evaluate(self, context=None):
        return self._parsed_expression.evaluate(context=context)

