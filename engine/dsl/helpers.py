import types
import murano_object
import yaql
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


def parse_yaql_structure(structure):
    if isinstance(structure, types.DictionaryType):
        result = {}
        for d_key, d_value in structure.iteritems():
            result[d_key] = parse_yaql_structure(d_value)
        return result
    elif isinstance(structure, types.ListType):
        return [parse_yaql_structure(t) for t in structure]
    elif isinstance(structure, types.StringTypes):
        return yaql.parse(structure)
    else:
        return structure


def evaluate_structure(structure, data, context):
    if isinstance(structure, types.DictionaryType):
        result = {}
        for d_key, d_value in structure.iteritems():
            result[d_key] = evaluate_structure(d_value, data, context)
        return result
    elif isinstance(structure, types.ListType):
        return [evaluate_structure(t, data, context) for t in structure]
    elif isinstance(structure, yaql.expressions.Expression):
        return structure.evaluate(data, context)
    else:
        return structure