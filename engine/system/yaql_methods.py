import re
import types


def _transform_json(json, mappings):
    if isinstance(json, types.ListType):
        return [_transform_json(t, mappings) for t in json]

    if isinstance(json, types.DictionaryType):
        result = {}
        for key, value in json.items():
            result[_transform_json(key, mappings)] = \
                _transform_json(value, mappings)
        return result

    elif isinstance(json, types.ListType):
        result = []
        for value in json:
            result.append(_transform_json(value, mappings))
        return result

    elif isinstance(json, types.StringTypes) and json.startswith('$'):
        value = _convert_macro_parameter(json[1:], mappings)
        if value is not None:
            return value

    return json


def _convert_macro_parameter(macro, mappings):
    replaced = [False]

    def replace(match):
        replaced[0] = True
        return unicode(mappings.get(match.group(1)))

    result = re.sub('{(\\w+?)}', replace, macro)
    if replaced[0]:
        return result
    else:
        return mappings.get(macro)


def register(context):
    context.register_function(
        lambda json, mappings: _transform_json(json(), mappings()), 'bind')