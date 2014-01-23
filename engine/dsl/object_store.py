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

    def load(self, data, context):
        tmp_store = ObjectStore(self._class_loader, self)
        for key, value in data.iteritems():
            if '?' not in value or 'type' not in value['?']:
                raise ValueError(key)
            system_key = value['?']
            del value['?']
            obj_type = system_key['type']
            class_obj = self._class_loader.get_class(obj_type)
            if not class_obj:
                raise ValueError()
            obj = class_obj.new(tmp_store, context=context, object_id=key)
            tmp_store._store[key] = obj
            obj.initialize(**value)
        loaded_objects = tmp_store._store.values()
        self._store.update(tmp_store._store)
        return loaded_objects