class Value(object):
    _immutable_ = True
    _attrs_ = []
    __slots__ = []

    def __repr__(self):
        return 'NULL'


class BoolValue(Value):
    _immutable_ = True
    _immutable_fields_ = ['value']
    _attrs_ = ['value']
    __slots__ = ['value']

    def __init__(self, value=False):
        assert isinstance(value, bool)
        self.value = value

    def __repr__(self):
        return 'true' if self.value else 'false'


class IntValue(Value):
    _immutable_ = True
    _immutable_fields_ = ['value']
    _attrs_ = ['value']
    __slots__ = ['value']

    def __init__(self, value=0):
        assert isinstance(value, int)
        self.value = value

    def __repr__(self):
        return str(self.value)


class StringValue(Value):
    _immutable_ = True
    _immutable_fields_ = ['value']
    _attrs_ = ['value']
    __slots__ = ['value']

    def __init__(self, value=''):
        assert isinstance(value, str)
        self.value = value

    def __repr__(self):
        return '"%s"' % self.value
