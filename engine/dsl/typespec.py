import type_scheme


class ArgumentSpec(object):
    def __init__(self, declaration, namespace_resolver):
        self._namespace_resolver = namespace_resolver
        self._type_scheme = type_scheme.TypeScheme(
            declaration['Type'], self._namespace_resolver)
        self._default = declaration.get('Default')
        self._has_default = 'Default' in declaration

    def validate(self, value, object_store):
        return self._type_scheme.map(value, object_store)

    @property
    def default(self):
        return self._default

    @property
    def has_default(self):
        return self._has_default


class PropertySpec(object):
    def __init__(self, declaration, namespace_resolver):
        self._namespace_resolver = namespace_resolver
        self._type_scheme = type_scheme.TypeScheme(
            declaration['Type'], self._namespace_resolver)
        self._default = declaration.get('Default')
        self._has_default = 'Default' in declaration
        self._access = declaration.get('Access', 'Public')

    def validate(self, value, object_store):
        return self._type_scheme.map(value, object_store)

    @property
    def default(self):
        return self._default

    @property
    def has_default(self):
        return self._has_default

    @property
    def access(self):
        return self._access