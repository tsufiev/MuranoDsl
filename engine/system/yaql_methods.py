import base64
import engine.config as cfg
import re
import types
from oslo.config.cfg import ConfigOpts, OptGroup
from yaql.context import EvalArg


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


@EvalArg('format', str)
def _format(format, *args):
    return format.format(*[t() for t in args])


@EvalArg('src', str)
@EvalArg('substring', str)
@EvalArg('value', str)
def _replace_str(src, substring, value):
    return src.replace(substring, value)


@EvalArg('src', str)
@EvalArg('replacements', dict)
def _replace_dict(src, replacements):
    for key, value in replacements.iteritems():
        src = src.replace(key, value)
    return src


def _len(value):
    return len(value())

def _coalesce(*args):
    for t in args:
        val = t()
        if val:
            return val
    return None


@EvalArg('value', str)
def _base64encode(value):
    return base64.b64encode(value)

@EvalArg('value', str)
def _base64decode(value):
    return base64.b64decode(value)


@EvalArg('group', str)
@EvalArg('setting', str)
def _config(group, setting):
    return cfg.CONF[group][setting]


@EvalArg('value', str)
def _upper(value):
    return value.upper()


@EvalArg('value', str)
def _lower(value):
    return value.lower()


@EvalArg('separator', str)
def _join(separator, *args):
    return separator.join([t() for t in args])


@EvalArg('value', str)
@EvalArg('separator', str)
def _split(value, separator):
    return value.split(separator)

def register(context):
    context.register_function(
        lambda json, mappings: _transform_json(json(), mappings()), 'bind')

    context.register_function(_format, 'format')
    context.register_function(_replace_str, 'replace')
    context.register_function(_replace_dict, 'replace')
    context.register_function(_len, 'len')
    context.register_function(_coalesce, 'coalesce')
    context.register_function(_base64decode, 'base64decode')
    context.register_function(_base64encode, 'base64encode')
    context.register_function(_config, 'config')
    context.register_function(_lower, 'lower')
    context.register_function(_upper, 'upper')
    context.register_function(_join, 'join')
    context.register_function(_split, 'split')

