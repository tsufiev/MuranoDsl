import re
import types
import yaql
import yaql.exceptions
from engine.dsl import helpers


class MuranoDslInstruction(object):
    @staticmethod
    def parse(instruction, evaluate_parameters=True):
        if isinstance(instruction, types.StringType):
            instruction = {instruction: None}
        if len(instruction) != 1:
            raise ValueError()

        key = instruction.keys()[0]
        if re.match(r'^\s*\$[.\w]+\s*=\s*.+$', key):
            return ExpressionInstruction(instruction, evaluate_parameters)
        if re.match(r'^\s*\$[.\w]+\s*$', key):
            return InitializationInstruction(instruction, evaluate_parameters)
        return ActionRequestInstruction(instruction, evaluate_parameters)


class ExpressionInstruction(MuranoDslInstruction):
    def __init__(self, instruction, evaluate_parameters=True):
        key = instruction.keys()[0]
        match = re.match(r'^\s*(\$[.\w]+)\s*=(\s*.+$)', key)
        self._assign_to = match.group(1)
        self._assign_to_container = None
        parts = self._assign_to.rsplit('.', 1)
        if len(parts) == 2:
            self._assign_to = parts[1]
            self._assign_to_container = yaql.parse(parts[0])
        self._expression = yaql.parse(match.group(2))

    @property
    def assign_to(self):
        return self._assign_to

    @property
    def assign_to_container(self):
        return self._assign_to_container

    @property
    def expression(self):
        return self._expression


class InitializationInstruction(MuranoDslInstruction):
    def __init__(self, instruction, evaluate_parameters=True):
        key = instruction.keys()[0]
        self._assign_to = key
        self._assign_to_container = None
        parts = self._assign_to.rsplit('.', 1)
        if len(parts) == 2:
            self._assign_to = parts[1]
            self._assign_to_container = yaql.parse(parts[0])
        self._value = instruction[key] if not evaluate_parameters \
            else helpers.parse_yaql_structure(instruction[key])

    @property
    def assign_to(self):
        return self._assign_to

    @property
    def assign_to_container(self):
        return self._assign_to_container

    @property
    def value(self):
        return self._value


class ActionRequestInstruction(MuranoDslInstruction):
    def __init__(self, instruction, evaluate_parameters=True):
        self._method_name = None
        self._target_obj = None

        key = instruction.keys()[0]
        value = instruction.values()[0]
        self._parse_key(key)
        self._parse_parameters(value, evaluate_parameters)

    @property
    def target_object(self):
        return self._target_obj

    def _parse_key(self, key):
        pattern = r'^\s*([\w:]+)\s*(.+)?\s*$'
        match = re.match(pattern, key)

        if match:
            self._method_name = match.group(1)
            self._target_obj = match.group(2)
        else:
            raise ValueError()

    def _parse_parameters(self, value, evaluate_parameters):
        if isinstance(value, types.ListType):
            self._parameters = dict([(i+1, v) for i, v in enumerate(value)])
        elif not isinstance(value, types.DictionaryType):
            self._parameters = {1: value}
        else:
            self._parameters = value
        if evaluate_parameters:
            for parameter_name, parameter_value in \
                    self._parameters.iteritems():
                self._parameters[parameter_name] = \
                    helpers.parse_yaql_structure(parameter_value) \
                    if evaluate_parameters else parameter_value


    @property
    def method_name(self):
        return self._method_name


    @property
    def parameters(self):
        return self._parameters

