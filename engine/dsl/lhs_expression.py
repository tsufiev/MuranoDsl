import inspect
import types
import yaql
import yaql.expressions
from murano_object import MuranoObject


class LhsExpression(object):
    def __init__(self, expression):
        expression = str(expression).strip()
        if not expression or expression == '$' or \
                not expression.startswith('$'):
                    raise SyntaxError()

        self._expression = yaql.parse(expression)

    def _set_value(self, container, key, value, object_store, murano_class):
        if inspect.isgenerator(container):
            for t in container:
                self._set_value(t, key, value, object_store, murano_class)
        elif inspect.isgenerator(key):
            for t in key:
                self._set_value(container, t, value,
                                object_store, murano_class)
        elif isinstance(container, types.DictionaryType):
            container[key] = value
        elif isinstance(container, MuranoObject):
            container.set_property(key, value, object_store, murano_class)
        elif isinstance(container, types.ListType) and \
                isinstance(key, types.IntType):
            container[key] = value
        else:
            raise ValueError()

    def set(self, value, context, object_store, murano_class):
        if isinstance(self._expression, (yaql.expressions.Att,
                                         yaql.expressions.Filter)):
            container = self._expression.object.evaluate(
                context=context)
            attr = self._expression.args[0].evaluate(context=context)
            self._set_value(container, attr, value,
                            object_store, murano_class)
        elif isinstance(self._expression, yaql.expressions.GetContextValue):
            path = self._expression.path.evaluate(context=context)
            context.set_data(value, path)
        else:
            raise SyntaxError()

    def get(self, context):
        return self._expression.evaluate(context=context)
