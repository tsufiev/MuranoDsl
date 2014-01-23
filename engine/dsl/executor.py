import functools
import inspect
import yaql
import yaql.exceptions
import types
import expressions
import exceptions
from yaql.context import ContextAware, EvalArg
from engine.dsl import helpers, MuranoObject, ObjectStore


class MuranoDslExecutor(object):
    def __init__(self, class_loader):
        self._class_loader = class_loader
        self._object_store = ObjectStore(class_loader)
        self._root_context = class_loader.create_root_context()
        self._root_context.set_data(self, '?executor')

        @ContextAware()
        def resolve(context, name, obj):
            return self._resolve(context, name, obj)

        self._root_context.register_function(resolve, '#resolve')

        @EvalArg('name', str)
        @ContextAware()
        def new(context, name, *args):
            if not '.' in name:
                murano_class = context.get_data('$?type')
                name = murano_class.namespace_resolver.resolve_name(name)
            parameters = {}
            arg_values = [t() for t in args]
            if len(arg_values) == 1 and isinstance(
                    arg_values[0], types.DictionaryType):
                parameters = arg_values[0]
            elif len(arg_values) > 0:
                for p in arg_values:
                    if not isinstance(p, types.TupleType) or \
                            not isinstance(p[0], types.StringType):
                            raise SyntaxError()
                    parameters[p[0]] = p[1]

            return self._class_loader.get_class(name).new(
                self._object_store, context, parameters=parameters)

        self._root_context.register_function(new, 'new')


    def _resolve(self, context, name, obj):
        @EvalArg('this', MuranoObject)
        def invoke(this, *args):
            try:

                murano_class = context.get_data('$?type')
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

        if callable(body):
            if '_context' in inspect.getargspec(body).args:
                params['_context'] = context
            if inspect.ismethod(body) and not body.__self__:
                return body(this, **params)
            else:
                return body(**params)
        elif isinstance(body, expressions.DslExpression):
            return self.execute(body, method.murano_class, this, params)
        else:
            raise ValueError()

    def _evaluate_parameters(self, arguments_scheme, context, *args):
        arg_names = list(arguments_scheme.keys())
        parameter_values = {}
        i = 0
        for arg in args:
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
                i += 1

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

    def execute(self, expression, murano_class, this, parameters={}):
        new_context = self._object_store.class_loader.create_local_context(
            parent_context=self._root_context,
            murano_class=murano_class)
        new_context.set_data(this)
        new_context.set_data(murano_class, '?type')

        @EvalArg('this', arg_type=MuranoObject)
        @EvalArg('property_name', arg_type=str)
        def obj_attribution(this, property_name):
            return this.get_property(property_name, murano_class)


        @EvalArg('prefix', str)
        @EvalArg('name', str)
        def validate(prefix, name):
            return murano_class.namespace_resolver.resolve_name(
                '%s:%s' % (prefix, name))

        new_context.register_function(obj_attribution, '#operator_.')
        new_context.register_function(validate, '#validate')

        for key, value in parameters.iteritems():
            new_context.set_data(value, key)
        return expression.execute(
            new_context, self._object_store, murano_class)

    def load(self, data):
        return self._object_store.load(data, self._root_context)
