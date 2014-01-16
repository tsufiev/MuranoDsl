import inspect
import types
import yaql
from yaql.context import EvalArg


class MuranoClassLoader(object):
    def __init__(self):
        self._system_classes = {}

    def get_class(self, name):
        pass

    def create_context(self):
        context = yaql.create_context(True)
        for obj in self._system_classes.values():
            self.__register_class(obj, context)
        return context

    def register_system_class(self, name, obj):
        self._system_classes[name] = obj

    def get_system_class(self, name):
        return self._system_classes.get(name)

    def __register_method(self, method, context):
        @EvalArg('this', arg_type=method.im_class)
        def f(this, *args):
            pargs = []
            kwargs = {}
            for arg in args:
                value = arg()
                if isinstance(value, types.TupleType) and len(value) == 2 and \
                        isinstance(value[0], types.StringTypes):
                    kwargs[value[0]] = value[1]
                else:
                    pargs.append(value)

            return method(self, *pargs, **kwargs)
        context.register_function(f, method.__name__)

    def __register_class(self, obj, context):
        cls = type(obj)
        for name in dir(cls):
            if name.startswith('_'):
                continue
            method = getattr(cls, name)
            if inspect.ismethod(method):
                self.__register_method(method, context)
