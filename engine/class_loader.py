import os.path
import types
import yaml

import dsl
import dsl.typespec


class ClassLoader(dsl.MuranoClassLoader):
    def __init__(self, base_path):
        self._base_path = base_path
        self._loaded_types = {}

    def get_class(self, name):
        if name in self._loaded_types:
            return self._loaded_types[name]

        path = os.path.join(self._base_path, name, 'manifest.yaml')
        with open(path) as stream:
            data = yaml.load(stream)
            #print data

        namespace_resolver = dsl.NamespaceResolver(data.get('Namespaces', {}))

        class_parents = data.get('Inherits')
        if class_parents:
            if not isinstance(class_parents, types.ListType):
                class_parents = [class_parents]
            for i, parent in enumerate(class_parents):
                class_parents[i] = self.get_class(
                    namespace_resolver.resolve_name(parent))
        type_obj = dsl.MuranoClass(self, namespace_resolver, name,
                                   class_parents)
        for property_name, property_spec in data.get('Properties',
                {}).iteritems():
            typespec = dsl.typespec.PropertySpec(property_spec,
                                                     namespace_resolver)
            type_obj.add_property(property_name, typespec)

        for method_name, payload in data.get('Workflow', {}).iteritems():
            method = type_obj.add_method(method_name, payload)

        self._loaded_types[name] = type_obj
        return type_obj

