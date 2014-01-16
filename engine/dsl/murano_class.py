from murano_method import MuranoMethod
from dsl_instruction import MuranoDslInstruction
from murano_object import MuranoObject
from typespec import PropertySpec


class MuranoClass(object):
    def __init__(self, class_loader, namespace_resolver, name, parents=None):
        self._class_loader = class_loader
        self._methods = {}
        self._namespace_resolver = namespace_resolver
        self._name = namespace_resolver.resolve_name(name)
        self._properties = {}
        if self._name == 'com.mirantis.murano.Object':
            self._parents = []
        else:
            self._parents = parents or [
                class_loader.get_class('com.mirantis.murano.Object')]

    @property
    def name(self):
        return self._name

    @property
    def parents(self):
        return self._parents

    @property
    def methods(self):
        return self._methods

    def get_method(self, name):
        return self._methods.get(
            self._namespace_resolver.resolve_name(name, self.name))

    def add_method(self, name, payload):
        name = self._namespace_resolver.resolve_name(name, self.name)
        method = MuranoMethod(self._namespace_resolver,
                              self, name, payload)
        self._methods[name] = method
        return method

    @property
    def properties(self):
        return self._properties.keys()

    def add_property(self, name, property_typespec):
        if not isinstance(property_typespec, PropertySpec):
            raise TypeError('property_typespec')
        self._properties[name] = property_typespec

    def get_property(self, name):
        return self._properties[name]

    def find_method(self, name):
        resolved_name = self._namespace_resolver.resolve_name(name, self.name)
        if resolved_name in self._methods:
            return [self]
        if not self._parents:
            return []
        return list(set(reduce(
            lambda x, y: x + y,
            [p.find_method(name) for p in self._parents])))

    def invoke(self, name, executor, parameters=None, this=None):
        return executor.execute_instruction(
            MuranoDslInstruction.parse({name: parameters}, False),
            this, None, self)

    def is_compatible(self, obj):
        if not isinstance(obj, MuranoObject):
            return False
        if obj.type is self:
            return True
        for t in self.parents:
            if t.is_compatible(obj):
                return True
        return False


