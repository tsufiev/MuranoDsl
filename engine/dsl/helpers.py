import re
import types
import murano_object
from yaql_expression import YaqlExpression
import yaql.expressions

def serialize(value):
    if isinstance(value, types.DictionaryType):
        result = {}
        for d_key, d_value in value.iteritems():
            result[d_key] = serialize(d_value)
        return result
    elif isinstance(value, murano_object.MuranoObject):
        return serialize(value.to_dictionary())
    elif isinstance(value, types.ListType):
        return [serialize(t) for t in value]
    else:
        return value

def evaluate(value, context):
    if isinstance(value, types.DictionaryType):
        result = {}
        for d_key, d_value in value.iteritems():
            result[d_key] = evaluate(d_value, context)
        return result
    elif isinstance(value, types.ListType):
        return [evaluate(t, context) for t in value]
    elif isinstance(value, YaqlExpression):
        return value.evaluate(context)
    elif isinstance(value, yaql.expressions.Expression):
        return value.evaluate(context)
    else:
        return value


def to_python_codestyle(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
