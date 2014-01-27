import os.path
import json as jsonlib
import yaml as yamllib

from engine.dsl import MuranoObject


class ResourceManager(MuranoObject):
    def initialize(self, base_path, _context, _class):
        if _class is None:
            _class = _context.get_data('$')
        class_name = _class.type.name
        self._base_path = os.path.join(base_path, class_name, 'resources')

    def string(self, name):
        path = os.path.join(self._base_path, name)
        with open(path) as file:
            return file.read()

    def json(self, name):
        return jsonlib.loads(self.string(name))

    def yaml(self, name):
        return yamllib.load(self.string(name))
