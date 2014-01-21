from collections import OrderedDict
import inspect
import types

import typespec
import macros


class MuranoMethod(object):
    def __init__(self, namespace_resolver,
                 murano_class, name, payload):
        self._name = name
        self._namespace_resolver = namespace_resolver

        if inspect.isfunction(payload):
            self._body = payload
            self._arguments_scheme = self._generate_arguments_scheme(payload)
        else:
            self._body = self._prepare_body(payload.get('Body', []))
            arguments_scheme = payload.get('Arguments')
            if arguments_scheme is None:
                self._arguments_scheme = {}
            else:
                if isinstance(arguments_scheme, types.DictionaryType):
                    self._arguments_scheme = \
                        typespec.ArgumentSpec(arguments_scheme,
                                                  self._namespace_resolver)
                else:
                    self._arguments_scheme = OrderedDict()
                    for record in arguments_scheme:
                        if not isinstance(record, types.DictionaryType) \
                                or len(record) > 1:
                                raise ValueError()
                        name = record.keys()[0]
                        self._arguments_scheme[name] = \
                            typespec.ArgumentSpec(record[name],
                                                      self._namespace_resolver)

        self._murano_class = murano_class

    @property
    def name(self):
        return self._name

    @property
    def murano_class(self):
        return self._murano_class

    @property
    def arguments_scheme(self):
        return self._arguments_scheme

    @property
    def body(self):
        return self._body

    def _generate_arguments_scheme(self, func):
        func_info = inspect.getargspec(func)
        data = [(name, {'Type': 'Object'}) for name in func_info.args]
        defaults = func_info.defaults or tuple()
        for i in xrange(len(defaults)):
            data[i + len(data) - len(defaults)][1]['Default'] = defaults[i]
        return OrderedDict([
            (name, typespec.ArgumentSpec(declaration,
                                             self._namespace_resolver))
            for name, declaration in data])

    def _prepare_body(self, body):
        return macros.MethodBlock(body)


