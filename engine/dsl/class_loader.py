import inspect
import types
import yaql
import yaql.context
import exceptions
from namespace_resolver import NamespaceResolver
from murano_class import MuranoClass, MuranoObject
import typespec


class MuranoClassLoader(object):
    def __init__(self):
        self._loaded_types = {}

    def get_class(self, name, create_missing=False):
        if name in self._loaded_types:
            return self._loaded_types[name]

        data = self.load_definition(name)
        if data is None:
            if create_missing:
                data = {'Name': name}
            else:
                raise exceptions.NoClassFound(name)

        namespace_resolver = NamespaceResolver(data.get('Namespaces', {}))

        class_parents = data.get('Inherits')
        if class_parents:
            if not isinstance(class_parents, types.ListType):
                class_parents = [class_parents]
            for i, parent in enumerate(class_parents):
                class_parents[i] = self.get_class(
                    namespace_resolver.resolve_name(parent))
        type_obj = MuranoClass(self, namespace_resolver, name,
                                   class_parents)
        for property_name, property_spec in data.get('Properties',
                {}).iteritems():
            spec = typespec.PropertySpec(property_spec, namespace_resolver)
            type_obj.add_property(property_name, spec)

        for method_name, payload in data.get('Workflow', {}).iteritems():
            method = type_obj.add_method(method_name, payload)

        self._loaded_types[name] = type_obj
        return type_obj

    def load_definition(self, name):
        raise NotImplementedError()

    def create_root_context(self):
        return yaql.create_context(True)

    def create_local_context(self, parent_context, murano_class):
        return yaql.context.Context(parent_context=parent_context)

    def _fix_parameters(self, kwargs):
        result = {}
        for key, value in kwargs.iteritems():
            if key in ('class', 'for', 'from', 'is', 'lambda', 'as',
                       'exec', 'assert', 'and', 'or', 'break', 'def',
                       'del', 'try', 'while', 'yield', 'raise', 'while',
                       'pass', 'return', 'not', 'print', 'in', 'import',
                       'global', 'if', 'finally', 'except', 'else', 'elif',
                       'continue', 'yield'):
                key = '_' + key
            result[key] = value
        return result


    def import_class(self, cls, name=None):
        if not name:
            if inspect.isclass(cls):
                name = cls._murano_class_name
            else:
                name = cls.__class__._murano_class_name

        murano_class = self.get_class(name, create_missing=True)

        if inspect.isclass(cls):
            if issubclass(cls, MuranoObject):
                def create_cls(object_store, context, parameters):
                    result = cls(murano_class, object_store)
                    parameters = self._fix_parameters(parameters)
                    if '_context' in inspect.getargspec(
                            result.initialize).args:
                        parameters['_context'] = context
                    result.initialize(**parameters)
                    return result
                murano_class.new = create_cls
            else:
                cls = cls()

        for item in dir(cls):
            method = getattr(cls, item)
            if callable(method) and not item.startswith('_'):
                murano_class.add_method(item, method)
