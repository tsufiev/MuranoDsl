from engine.dsl.murano_object import MuranoObject


class ObjectStore(object):
    def __init__(self, class_loader, parent_store=None):
        self._class_loader = class_loader
        self._parent_store = parent_store
        self._store = {}

    @property
    def class_loader(self):
        return self._class_loader

    def get(self, object_id):
        if object_id in self._store:
            return self._store[object_id]
        if self._parent_store:
            return self._parent_store.get(object_id)
        return None

    def load(self, data):
        tmp_store = ObjectStore(self._class_loader, self)
        for key, value in data.iteritems():
            if '?' not in value or 'type' not in value['?']:
                raise ValueError(key)
            obj_type = value['?']['type']
            class_obj = self._class_loader.get_class(obj_type)
            if not class_obj:
                raise ValueError()
            obj = MuranoObject(class_obj, key)
            tmp_store._store[key] = obj
            for property_name, property_value in value.iteritems():
                if property_name.startswith('?'):
                    continue
                obj.set_property(property_name, property_value, tmp_store)
        loaded_objects = tmp_store._store.values()
        self._store.update(tmp_store._store)
        return loaded_objects