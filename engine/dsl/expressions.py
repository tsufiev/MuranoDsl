import types
from lhs_expression import LhsExpression
import helpers
from yaql_expression import YaqlExpression

_macros = []


def register_macro(cls):
    _macros.append(cls)


class DslExpression(object):
    def execute(self, context, object_store, murano_class):
        pass


class Statement(DslExpression):
    def __init__(self, statement):
        if isinstance(statement, YaqlExpression):
            key = None
            value = statement
        elif isinstance(statement, types.DictionaryType):
            if len(statement) != 1:
                raise SyntaxError()
            key = statement.keys()[0]
            value = statement[key]
        else:
            raise SyntaxError()

        self._destination = None if not key else LhsExpression(key)
        self._expression = value

    @property
    def destination(self):
        return self._destination

    @property
    def expression(self):
        return self._expression

    def execute(self, context, object_store, murano_class):
        result = helpers.evaluate(self.expression, context)
        if self.destination:
            self.destination.set(result, context, object_store, murano_class)

        return result


def parse_expression(expr):
    if isinstance(expr, YaqlExpression):
        return Statement(expr)
    elif isinstance(expr, types.DictionaryType):
        kwds = {}
        for key, value in expr.iteritems():
            key = str(key).strip()
            if not key:
                raise SyntaxError()
            if key.startswith('$'):
                return Statement(expr)
            parts = key.split(' ', 1)
            kwds[parts[0]] = \
                (None if len(parts) == 1 else parts[1]), value

        for cls in _macros:
            try:
                return cls(**kwds)
            except TypeError:
                continue

        return Statement(expr)

    raise SyntaxError()






