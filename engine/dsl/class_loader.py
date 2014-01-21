import inspect
import types
import yaql
from yaql.context import EvalArg
from namespace_resolver import NamespaceResolver
from murano_class import MuranoClass

import typespec

class MuranoClassLoader(object):
    def __init__(self):
        self._loaded_types = {}

    def get_class(self, name):
        if name in self._loaded_types:
            return self._loaded_types[name]

        data = self.load_definition(name)

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
