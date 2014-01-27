import os.path
import yaml

import dsl
import dsl.typespec
from dsl.yaql_expression import YaqlExpression
import system.yaql_methods

def yaql_constructor(loader, node):
    value = loader.construct_scalar(node)
    return YaqlExpression(value)


yaml.add_constructor(u'!yaql', yaql_constructor)
yaml.add_implicit_resolver(u'!yaql', YaqlExpression)


class ClassLoader(dsl.MuranoClassLoader):
    def __init__(self, base_path):
        super(ClassLoader, self).__init__()
        self._base_path = base_path

    def load_definition(self, name):
        path = os.path.join(self._base_path, name, 'manifest.yaml')
        if not os.path.exists(path):
            return None
        with open(path) as stream:
            return yaml.load(stream)

    def create_root_context(self):
        context = super(ClassLoader, self).create_root_context()
        system.yaql_methods.register(context)
        return context

