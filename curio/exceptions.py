
class NamedObjectError(RuntimeError):
    def __init__(self, name, **meta):
        self.name = name
        self.meta = meta

class CurioLocked(NamedObjectError):
    def __str__(self):
        return '"%s" is locked' % self.name

class UnsetKey(NamedObjectError):
    def __str__(self):
        return 'the key "%s" has no value' % self.name
