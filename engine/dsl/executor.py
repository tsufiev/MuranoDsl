import inspect
import functools
import yaql
import yaql.exceptions
import types
import expressions
import exceptions
from yaql.context import Context, ContextAware, EvalArg
from engine.dsl import helpers, MuranoObject


class MuranoDslExecutor(object):
    def __init__(self, object_store):
        self._object_store = object_store
        self._root_context = yaql.create_context(True)

        @ContextAware()
        def resolve(context, name, obj):
            return self._resolve(context, name, obj)

        self._root_context.register_function(resolve, '#resolve')

    def _resolve(self, context, name, obj):
        @EvalArg('this', MuranoObject)
        def invoke(this, *args):
            try:
                murano_class = helpers.evaluate('type()', context)
                return self.invoke_method(name, obj, context,
                                          murano_class, *args)
            except exceptions.NoMethodFound:
                raise yaql.exceptions.YaqlExecutionException()
            except exceptions.AmbiguousMethodName:
                raise yaql.exceptions.YaqlExecutionException()

        if not isinstance(obj, MuranoObject):
            return None

        return invoke

    def to_yaql_args(self, args):
        if not args:
            return tuple()
        elif isinstance(args, types.TupleType):
            return args
        elif isinstance(args, types.ListType):
            return tuple(args)
        elif isinstance(args, types.DictionaryType):
            return tuple(args.items())
        else:
            raise ValueError()

    def invoke_method(self, name, this, context, murano_class, *args):
        if context is None:
            context = self._root_context
        implementations = this.type.find_method(name)
        delegates = []
        for declaring_class, name in implementations:
            method = declaring_class.get_method(name)
            if not method:
                continue
            arguments_scheme = method.arguments_scheme
            try:
                params = self._evaluate_parameters(
                    arguments_scheme, context, *args)
                delegates.append(functools.partial(
                    self._invoke_method_implementation,
                    method, this, context, params))
            except TypeError:
                continue
        if len(delegates) < 1:
            raise exceptions.NoMethodFound(name)
        elif len(delegates) > 1:
            raise exceptions.AmbiguousMethodName(name)
        else:
            return delegates[0]()

    def _invoke_method_implementation(self, method, this, context, params):
        body = method.body
        if not body:
            return None

        if inspect.isfunction(body):
            return body(**params)
        elif isinstance(body, expressions.DslExpression):
            return self.execute(body, method.murano_class, this,
                                context, params)
        else:
            raise ValueError()

    def _evaluate_parameters(self, arguments_scheme, context, *args):
        arg_names = list(arguments_scheme.keys())
        parameter_values = {}
        for i, arg in enumerate(args):
            value = helpers.evaluate(arg, context)
            if isinstance(value, types.TupleType) and len(value) == 2 and \
                    isinstance(value[0], types.StringTypes):
                name = value[0]
                value = value[1]
                if name not in arguments_scheme:
                    raise TypeError()
            else:
                if i >= len(arg_names):
                    raise TypeError()
                name = arg_names[i]

            if callable(value):
                value = value()
            arg_spec = arguments_scheme[name]
            parameter_values[name] = arg_spec.validate(
                value, self._object_store)

        for name, arg_spec in arguments_scheme.iteritems():
            if name not in parameter_values:
                if not arg_spec.has_default:
                    raise TypeError()
                parameter_values[name] = arg_spec.validate(
                    arg_spec.default, self._object_store)

        return parameter_values

    def execute(self, expression, murano_class, this, context=None,
                parameters={}):
        new_context = Context(parent_context=context or self._root_context)
        new_context.set_data(this)
        new_context.register_function(lambda: murano_class, 'type')

        @EvalArg('this', arg_type=MuranoObject)
        @EvalArg('property_name', arg_type=str)
        def obj_attribution(this, property_name):
            return this.get_property(property_name, murano_class)

        new_context.register_function(obj_attribution, '#operator_.')

        for key, value in parameters.iteritems():
            new_context.set_data(value, key)
        return expression.execute(
            new_context, self._object_store, murano_class)


