import os.path
import json as jsonlib

from engine.dsl import MuranoObject


class ResourceManager(MuranoObject):
    def initialize(self, base_path, _context, _class):
        if _class is None:
            _class = _context.get_data('$')
        class_name = _class.type.name
        self._base_path = os.path.join(base_path, class_name, 'resources')
        print _context

    def json(self, name):
        path = os.path.join(self._base_path, name)
        with open(path) as file:
            return jsonlib.loads(file.read())
