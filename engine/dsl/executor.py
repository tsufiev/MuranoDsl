import inspect
import types
import eventlet
import yaql
import yaql.expressions
import helpers

from yaql.context import Context, EvalArg, ContextAware
from murano_object import MuranoObject

import dsl_instruction

class MuranoDslExecutor(object):
    def __init__(self, object_store):
        self._object_store = object_store
        self._root_context = yaql.create_context(True)

    def execute_instruction(self, instruction, this, context, root_class):
        if context is None:
            context = self._create_context(root_class)

        if isinstance(instruction, dsl_instruction.ExpressionInstruction):
            result = instruction.expression.evaluate(this, context)
            self._set_result(result, instruction, this, context, root_class)
        elif isinstance(instruction,
                        dsl_instruction.InitializationInstruction):
            result = helpers.evaluate_structure(
                instruction.value, this, context)
            self._set_result(result, instruction, this, context, root_class)
        else:
            target_object = this
            if instruction.target_object is not None:
                target_object = instruction.target_object.evaluate(
                    this, context)
                if not isinstance(target_object, MuranoObject):
                    raise TypeError()

            if not target_object:
                target_object = [None]
            elif not isinstance(target_object, types.ListType):
                target_object = [target_object]

            method_types = root_class.find_method(instruction.method_name)
            if not method_types:
                raise LookupError(
                    'Method %s not found' % instruction.method_name)
            gp = eventlet.greenpool.GreenPile(
                len(method_types) * len(target_object))
            for murano_class in method_types:
                for obj in target_object:
                    target_class = root_class
                    if target_object is not None:
                        target_class = obj.type

                    gp.spawn(self._call, murano_class, instruction, obj,
                             self._create_context(target_class, context))
            result = [t for t in gp]

    def _call(self, murano_class, instruction, this, context):
        method_name, parameters = \
            instruction.method_name, instruction.parameters

        method = murano_class.get_method(method_name)
        argument_scheme = method.arguments_scheme
        parameter_values = self._evaluate_parameters(argument_scheme,
                                                     parameters, this,
                                                     context)

        self.execute_method(method, parameter_values, this)

    def _set_result(self, result, instruction, this, context, murano_class):
        # if this is not None:
        #     murano_class = this.type
        if not instruction.assign_to:
            return
        container = context
        if instruction.assign_to_container is not None:
            container = instruction.assign_to_container.evaluate(this, context)
        if isinstance(container, Context):
            container.set_data(result, instruction.assign_to)
        elif isinstance(container, MuranoObject):
            container.set_property(instruction.assign_to, result,
                                   self._object_store, murano_class)
        else:
            raise ValueError()

    def execute_method(self, method, parameters=None, this=None):
        body = method.body
        if not body:
            return None

        local_context = self._create_context(method.murano_class)
        if parameters:
            for key, value in parameters.iteritems():
                local_context.set_data(value, key)

        parameter_values = self._evaluate_parameters(
            method.arguments_scheme, parameters, this, local_context)

        if inspect.isfunction(body):
            body(**parameter_values)
        else:
            for statement in body:
                self.execute_statement(statement, method, this, local_context)

    def _evaluate_parameters(self, arguments_scheme, parameters,
                             this, context):
        parameter_values = {}
        if parameters is None:
            parameters = {}
        elif isinstance(parameters, types.ListType):
            parameters = dict([(i+1, v) for i, v in enumerate(parameters)])
        elif not isinstance(parameters, types.DictionaryType):
            parameters = {1: parameters}

        for i, arg_name in enumerate(arguments_scheme):
            arg_typespec = arguments_scheme[arg_name]

            def eval_param(param):
                obj = parameters[param]
                if isinstance(obj, yaql.expressions.Expression):
                    obj = obj.evaluate(this, context)
                return arg_typespec.validate(obj, self._object_store)

            if arg_name in parameters:
                parameter_values[arg_name] = eval_param(arg_name)
            elif unicode(i+1) in parameters:
                parameter_values[arg_name] = eval_param(unicode(i+1))
            elif i+1 in parameters:
                parameter_values[arg_name] = eval_param(i+1)
            elif arg_typespec.has_default:
                parameter_values[arg_name] = arg_typespec.default
            else:
                raise ValueError()
        return parameter_values

    def execute_statement(self, statement, method, this, context):
        if len(statement) == 1:
            return self.execute_instruction(statement[0], this, context,
                                            method.murano_class)
        else:
            gp = eventlet.greenpool.GreenPile(len(statement))
            for instruction in statement:
                gp.spawn(self.execute_instruction, instruction,
                         this,
                         self._create_context(method.murano_class, context),
                         method.murano_class)
            return [t for t in gp]

    def _create_context(self, root_class, parent_context=None):
        @ContextAware(context_parameter_name='self_context')
        @EvalArg('self', arg_type=MuranoObject)
        @EvalArg('property_name', arg_type=str)
        def obj_attribution(self_context, self, property_name):
            return self.get_property(property_name, root_class)

        if parent_context is not None:
            return Context(parent_context=parent_context)
        else:
            context = Context(parent_context=self._root_context)
            context.register_function(obj_attribution, 'operator_.')
            return context



