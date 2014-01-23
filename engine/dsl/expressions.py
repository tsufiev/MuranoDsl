import types
import re
from murano_object import MuranoObject
import helpers
from yaql_expression import YaqlExpression
from yaql.context import Context

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

        self._assign_to = None
        self._assign_to_container = None
        if key:
            path = str(key).strip()
            if not re.match(r'^\s*\$[.\w]+\s*$', path):
                raise SyntaxError()
            self._assign_to = path
            parts = self._assign_to.rsplit('.', 1)
            if len(parts) == 2:
                self._assign_to = parts[1]
                self._assign_to_container = YaqlExpression(parts[0])

        self._expression = value

    @property
    def assign_to(self):
        return self._assign_to

    @property
    def assign_to_container(self):
        return self._assign_to_container

    @property
    def expression(self):
        return self._expression

    def execute(self, context, object_store, murano_class):
        result = helpers.evaluate(self.expression, context)

        if not self.assign_to:
            return None

        container = context
        if self.assign_to_container is not None:
            container = self.assign_to_container.evaluate(context)
        if isinstance(container, Context):
            container.set_data(result, self.assign_to)
        elif isinstance(container, MuranoObject):
            container.set_property(self.assign_to, result,
                                   object_store, murano_class)
        elif isinstance(container, types.DictionaryType):
            container[self.assign_to] = result
        elif isinstance(container, types.ListType):
            container[int(self.assign_to)] = result
        else:
            raise ValueError()

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
            if re.match(r'^\$[.\w]+$', key):
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






