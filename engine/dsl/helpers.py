import collections
import inspect
import deep
import re
import types
import murano_object
from yaql_expression import YaqlExpression
import yaql.expressions
from eventlet.greenpool import GreenMap

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
    elif isinstance(value, (YaqlExpression, yaql.expressions.Expression)):
        return evaluate(value.evaluate(context), context)
    elif isinstance(value, types.TupleType):
        return tuple(evaluate(list(value), context))
    elif callable(value):
        return value()
    elif isinstance(value, types.StringTypes):
        return value
    elif isinstance(value, collections.Iterable):
        return list(value)
    else:
        return value


def merge_lists(list1, list2):
    result = []
    for item in list1 + list2:
        exists = False
        for old_item in result:
            if deep.diff(item, old_item) is None:
                exists = True
                break
        if not exists:
            result.append(item)
    return result


def merge_dicts(dict1, dict2, max_levels=0):
    result = {}
    for key, value in dict1.items():
        result[key] = value
        if key in dict2:
            other_value = dict2[key]
            if type(other_value) != type(value):
                raise TypeError()
            if max_levels != 1 and isinstance(
                    other_value, types.DictionaryType):
                result[key] = merge_dicts(
                    value, other_value,
                    0 if max_levels == 0 else max_levels - 1)
            elif max_levels != 1 and isinstance(
                    other_value, types.ListType):
                result[key] = merge_lists(value, other_value)
            else:
                result[key] = other_value
    for key, value in dict2.items():
        if key not in result:
            result[key] = value
    return result


def to_python_codestyle(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def get_executor(context):
    return context.get_data('$?executor')


def get_type(context):
    return context.get_data('$?type')


def get_environment(context):
    return context.get_data('$?environment')


def get_object_store(context):
    return context.get_data('$?objectStore')