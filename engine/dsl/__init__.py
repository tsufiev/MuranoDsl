from class_loader import MuranoClassLoader
from murano_class import MuranoClass
from namespace_resolver import NamespaceResolver
from murano_object import MuranoObject
from object_store import ObjectStore
import macros

__all__ = ['MuranoClassLoader', 'MuranoClass', 'NamespaceResolver',
           'ObjectStore', 'MuranoObject']


def classname(name):
    def wrapper(cls):
        cls._murano_class_name = name
        return cls
    return wrapper