class NamespaceResolver(object):
    def __init__(self, namespaces):
        self._namespaces = namespaces
        self._namespaces[''] = ''

    def resolve_name(self, name, relative=None):
        if name is None:
            raise ValueError()
        if name and name.startswith(':'):
            return name[1:]
        if ':' in name:
            parts = name.split(':')
            if len(parts) != 2 or not parts[1]:
                raise NameError('Incorrectly formatted name ' + name)
            if parts[0] not in self._namespaces:
                raise KeyError('Unknown namespace prefix ' + parts[0])
            return '.'.join((self._namespaces[parts[0]], parts[1]))
        if not relative and '=' in self._namespaces and '.' not in name:
            return '.'.join((self._namespaces['='], name))
        if relative and '.' not in name:
            return '.'.join((relative, name))
        return name


