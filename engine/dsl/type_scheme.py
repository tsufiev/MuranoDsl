import types
import uuid


class TypeScheme(object):
    def __init__(self, typedef, namespace_resolver):
        self._typedef = typedef
        self._namespace_resolver = namespace_resolver

    def _map_dict(self, value, typedef, object_store):
        if not isinstance(value, types.DictionaryType):
            raise ValueError()
        if len(typedef) == 0:
            return value
        result = {}
        for key in typedef:
            target_key = key
            allow_none = False
            if key.endswith('?'):
                target_key = key[:-1]
                allow_none = True
            item_value = value.get(target_key)
            if item_value is None:
                if not allow_none:
                    raise ValueError()
                result[target_key] = None
                continue
            result[target_key] = self._map(item_value, typedef[key],
                                           object_store)
        return result

    def _map_list(self, value, typedef, object_store):
        if not isinstance(value, types.ListType):
            value = [value]
        if len(typedef) == 0:
            return value
        result = []
        for item in value:
            mapped_item = self._map(item, typedef[0], object_store)
            result.append(mapped_item)
        if len(typedef) >= 2 and len(result) < typedef[1]:
            raise ValueError()
        if len(typedef) >= 3 and len(result) > typedef[2]:
            raise ValueError()

        return result

    def _map_string(self, value, typedef):
        if value is None:
            return None
        return unicode(value)

    def _map_integer(self, value):
        return int(value)

    def _map_boolean(self, value):
        if value is True \
            or isinstance(value, types.IntType) and value != 0 \
                or isinstance(value, types.StringTypes) \
                and value.lower() == 'true':
            return True
        return False

    def _map_custom_class(self, value, typename, object_store):
        class_loader = object_store.class_loader
        dest_class = class_loader.get_class(typename)
        if not dest_class:
            raise TypeError()
        if isinstance(value, types.StringTypes):
            obj = object_store.get(value)
            if obj is None:
                raise ValueError()
            if not dest_class.is_compatible(obj):
                raise ValueError()
            return obj

        if isinstance(value, types.DictionaryType):
            if '?' not in value:
                value['?'] = {}
            if 'type' not in value['?']:
                value['?']['type'] = typename
            obj = object_store.load({uuid.uuid4().hex: value})[0]
            if not dest_class.is_compatible(obj):
                raise ValueError()
            return obj

    def _map(self, value, typedef, object_store):
        # if value is None:
        #     raise ValueError()
        if isinstance(typedef, types.DictionaryType):
            return self._map_dict(value, typedef, object_store)
        if isinstance(typedef, types.ListType):
            return self._map_list(value, typedef, object_store)
        if isinstance(typedef, types.StringTypes):
            if typedef == 'String':
                return self._map_string(value, typedef)
            if typedef == 'Integer':
                return self._map_integer(value)
            if typedef == 'Boolean':
                return self._map_boolean(value)
            if typedef == 'Object':
                return value
            full_name = self._namespace_resolver.resolve_name(typedef)
            return self._map_custom_class(value, full_name, object_store)

    def map(self, value, object_store):
        return self._map(value, self._typedef, object_store)
