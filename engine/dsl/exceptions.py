class ReturnException(Exception):
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value


class BreakException(Exception):
    pass


class NoMethodFound(Exception):
    def __init__(self, name):
        super(NoMethodFound, self).__init__('Method %s not found' % name)


class AmbiguousMethodName(Exception):
    def __init__(self, name):
        super(AmbiguousMethodName, self).__init__(
            'Found more that one method %s' % name)