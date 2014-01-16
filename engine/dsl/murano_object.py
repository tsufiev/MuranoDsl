import json
import types
import uuid
import yaml
import helpers


class MuranoObject(object):
    def __init__(self, murano_class, object_id=None):
        self._object_id = object_id or uuid.uuid4().hex
        self._type = murano_class
        self._properties = {}
        self._parents = {}
        for property_name in murano_class.properties:
            typespec = murano_class.get_property(property_name)
            self._properties[property_name] = typespec.default
        for parent in murano_class.parents:
            self._parents[parent.name] = MuranoObject(
                parent, self._object_id)

    @property
    def object_id(self):
        return self._object_id

    @property
    def type(self):
        return self._type

    def get_property(self, item, caller_class=None):
        print 'caller_class', caller_class.name
        if item in self._properties and \
                self._is_accessible(item, caller_class):
            return self._properties[item]
        i = 0
        result = None
        for parent in self._parents.values():
            try:
                result = parent.get_property(item, caller_class)
                i += 1
                if i > 1:
                    raise LookupError()
            except AttributeError:
                continue
        if not i:
            raise AttributeError()
        return result

    def set_property(self, key, value, object_store, caller_class=None):
        if key in self._properties and self._is_accessible(key, caller_class):
            spec = self._type.get_property(key)
            self._properties[key] = spec.validate(
                value, object_store)
        else:
            for parent in self._parents.values():
                try:
                    parent.set_property(key, value, object_store, caller_class)
                    return
                except AttributeError:
                    continue
            raise AttributeError()

    def _is_accessible(self, property_name, caller_class):
        spec = self._type.get_property(property_name)
        if not spec:
            return False
        if spec.access == 'Public':
            return True
        if caller_class == self.type:
            return True
        return False


    def __repr__(self):
        return yaml.dump(helpers.serialize(self))

    def to_dictionary(self):
        result = {}
        for parent in self._parents.values():
            result.update(parent.to_dictionary())
        result.update({'?': {'type': self.type.name, 'id': self.object_id}})
        result.update(self._properties)
        return result

