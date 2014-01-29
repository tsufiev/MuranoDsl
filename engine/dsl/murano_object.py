import json
import types
import uuid
import yaml
import helpers
from engine.consts import PARAMETERS_HISTORY_KEY, HISTORY_OBJECT_KEY_SUFFIX
from yaql_expression import YaqlExpression


class History(dict):
    def to_dictionary(self):
        dictionary = {}
        for key, value in self.iteritems():
            if isinstance(value, MuranoObject):
                dictionary[key+HISTORY_OBJECT_KEY_SUFFIX] = value.object_id
            else:
                dictionary[key] = value
        return dictionary

    def unpack(self, object_store):
        suffix_length = len(HISTORY_OBJECT_KEY_SUFFIX)
        for key, value in self.items():
            if key.endswith(HISTORY_OBJECT_KEY_SUFFIX):
                del self[key]
                actual_key = key[:-suffix_length]
                self[actual_key] = object_store.get(value)


class MuranoObject(object):
    def __init__(self, murano_class, object_store, object_id=None):
        self._object_id = object_id or uuid.uuid4().hex
        self._type = murano_class
        self._properties = {}
        self._history = History()
        self._object_store = object_store
        self._parents = {}
        for property_name in murano_class.properties:
            typespec = murano_class.get_property(property_name)
            self._properties[property_name] = typespec.default
        for parent in murano_class.parents:
            self._parents[parent.name] = MuranoObject(
                parent, self._object_id)

    def initialize(self, history=None, **kwargs):
        if history is None:
            history = {}
        for property_name, property_value in kwargs.iteritems():
            self.set_property(property_name, property_value,
                              self._object_store)
        for item, value in history.iteritems():
            self._history[item] = value

    def __eq__(self, other):
        return False  # for simplicity objects are never equal
        # if not isinstance(other, MuranoObject) or self.type != other.type:
        #     return False
        # else:
        #     for item in self.properties | other.properties:
        #         if not (self.property_visible(item) and
        #                 other.property_visible(item)):
        #             return False
        #         elif self.get_property(item) != other.get_property(item):
        #             return False
        # return True

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def properties(self):
        return set(self._properties.keys())

    @property
    def object_id(self):
        return self._object_id

    @property
    def type(self):
        return self._type

    def __getattr__(self, item):
        return self.get_property(item)

    def get_history(self, item):
        return self._history.get(item)

    def set_history(self, item, value, context):
        if isinstance(value, YaqlExpression):
            value = helpers.evaluate(value, context)
        self._history[item] = value

    def unpack_history(self, object_store):
        self._history.unpack(object_store)

    @staticmethod
    def _is_list_of_objs(lst):
        return not len(lst) or isinstance(lst[0], MuranoObject)

    @staticmethod
    def _diff_sets(old_set, new_set):
        old_set, new_set = set(old_set), set(new_set)
        return (list(old_set - new_set),  # exit
                list(new_set - old_set),  # enter
                list(new_set & old_set))  # possible update

    def diff(self, item, value, context, object_store):
        difference = {}
        prev_value = self.get_history(item)
        if isinstance(value, YaqlExpression):
            value = helpers.evaluate(value, context)

        if isinstance(value, types.ListType):
            if (not self._is_list_of_objs(value) or
                    not self._is_list_of_objs(prev_value)):
                raise ValueError('Only list of values can be compared!')
            exit_ids, enter_ids, common_ids = self._diff_sets(
                old_set=set([obj.object_id for obj in prev_value]),
                new_set=set([obj.object_id for obj in value]))
            update_ids = [
                obj.object_id for obj, prev_obj in
                zip([o for o in value if o.object_id in common_ids],
                    [o for o in prev_value if o.object_id in common_ids])
                if obj != prev_obj]
            difference.update({'enter': list(enter_ids),
                               'exit': list(exit_ids),
                               'update': list(update_ids)})
        elif isinstance(value, MuranoObject):
            if not isinstance(prev_value, (MuranoObject, types.NoneType)):
                raise ValueError('Objects can be compared with each '
                                 'other only')
            if prev_value is None:
                difference.update({'enter': value.object_id})
            elif value.object_id != prev_value.object_id:
                difference.update({'enter': value.object_id,
                                   'exit': prev_value.object_id})
            elif value != prev_value:
                difference.update({'update': value.object_id})
        elif isinstance(prev_value, MuranoObject) and value is None:
            difference.update({'exit': prev_value.object_id})
        else:  # diff atomic types returns True|False
            return value != prev_value

        return difference

    def property_visible(self, item, caller_class=None):
        if caller_class is None:
            caller_class = self.type
        return item in self._properties and \
            self._is_accessible(item, caller_class)

    def get_property(self, item, caller_class=None):
        #print 'caller_class', caller_class.name
        if self.property_visible(item, caller_class):
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
            raise AttributeError(key)

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
        result.update({
            '?': {'type': self.type.name, 'id': self.object_id,
                  PARAMETERS_HISTORY_KEY: self._history.to_dictionary()}})
        result.update(self._properties)
        return result
