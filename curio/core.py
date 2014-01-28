import os
import re
import fcntl
import cPickle as pickle
import time
try:
    # py 2.5+
    from hashlib import sha1 as sha
except ImportError:
    # py 2.4
    from sha import new as sha

from curio.exceptions import CurioLocked

HEX_LOWERCASE = 'abcdef0123456789'

def mkdir_p(directory):
    try:
        os.makedirs(directory)
    except OSError:
        if not os.path.isdir(directory):
            raise

def create_hex_dirs(parent_dir):
    mkdir_p(parent_dir)
    hex_dirs = map(lambda x: os.path.join(parent_dir, x), HEX_LOWERCASE)
    map(mkdir_p, hex_dirs)

class BaseLockManager(object):
    def lock(self, entity):
        raise NotImplementedError

    def unlock(self, entity):
        raise NotImplementedError

    def unlock_all(self):
        raise NotImplementedError

class LockManager(BaseLockManager):
    def __init__(self):
        self.locks = set()

    def lock(self, fd):
        try:
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB) # acquire the lock, non-blocking
        except IOError:
            raise CurioLocked(fd.name)
        self.locks.add(fd)

    def unlock(self, fd):
        if fd not in self.locks:
            return    

        fcntl.lockf(fd, fcntl.LOCK_UN)
        self.locks.remove(fd)

    def unlock_all(self):
        locks = list(self.locks)
        for lock in locks:
            self.unlock(lock)
        self.locks = set()

class Curio(object):
    def __init__(self, root):
        self.root = root
        # initialize the appropriate directories
        self.initialize_db()
        # manages entity locks
        self.locker = LockManager()

    def __del__(self):
        # on shutdown, remove all entity locks
        self.locker.unlock_all()

    def walk(self):
        for curdir, dirs, files in os.walk(self.root):
            for f in files:
                if not f.startswith('.'):
                    yield self.load_target(os.path.join(curdir, f))

    def initialize_db(self):
        mkdir_p(self.root)
        create_hex_dirs(self.root)
    
    def lock_entity(self, entity_name):
        target = self.generate_target(entity_name)
        if os.path.isfile(target):
            fd = open(target, 'a')
            while True:
                try:
                    self.locker.lock(fd)
                    break
                except IOError:
                    print 'locked!'
                    time.sleep(1)

    def unlock_entity(self, entity_name):
        target = self.generate_target(entity_name)
        if os.path.isfile(target):
            fd = open(target, 'a')
            self.locker.unlock(fd)

    def load_target(self, filename):
        return pickle.load(open(filename, 'rb'))

    def load(self, name):
        target = self.generate_target(name)
        if os.path.isfile(target):
            return self.load_target(target)
        else:
            # base entity, no data
            return {'__name__': name}

    def generate_target(self, name):
        hashed_name = sha(name).hexdigest()
        return os.path.join(self.root, hashed_name[0], hashed_name)

    def dump_target(self, data, filename):
        if data.keys() == ['__name__']: # i.e. no data, so delete the entity..
            os.remove(filename)
        else:
            pickle.dump(data, open(filename, 'wb'), pickle.HIGHEST_PROTOCOL)

    def dump(self, data, name):
        target = self.generate_target(name)
        data['__name__'] = name 
        self.dump_target(data, target)

class CurioManager(object):
    def __init__(self, uri):
        # open a cursor to the database
        self.db = Curio(uri)

    def get(self, entity_name, key):
        entity = self.db.load(entity_name)
        return entity.get(key, None)

    def set(self, entity_name, key, value):
        self.db.lock_entity(entity_name)
        entity = self.db.load(entity_name)
        entity[key] = value
        self.db.dump(entity, entity_name)
        self.db.unlock_entity(entity_name)

    def delete(self, entity_name, key):
        self.db.lock_entity(entity_name)
        entity = self.db.load(entity_name)
        if entity.has_key(key):
            del entity[key]
        self.db.dump(entity, entity_name)
        self.db.unlock_entity(entity_name)

    def find(self, entity_name=None, key=None):
        entity_name = entity_name or r'.*'
        key = key or r'.*'
        ENTITY_RE = re.compile(entity_name)
        KEY_RE = re.compile(key)
        results = {}
        # search all entities..
        for entity in self.db.walk():
            name = entity['__name__']
            # entity name must match..
            if not ENTITY_RE.match(name):
                continue
            results[name] = {}
            for key in entity.keys():
                # key name must match and not be a 'private' key
                if KEY_RE.match(key) and not key.startswith('_'):
                    results[name][key] = entity[key]
        return results

class CurioConfig(dict):
    def __init__(self, defaults={}):
        self.defaults = defaults
        dict.__init__(self, defaults)

    def update_from_env(self, env_mapping):
        # update from environment variables
        for key in env_mapping:
            env_val = os.environ.get(env_mapping[key])
            if env_val:
                self[key] = env_val
    
    def update_from_opts(self, opts):
        for key in self.defaults:
            val = getattr(opts, key, None)
            if val:
                self[key] = val
    
    def update_from_args(self, args):
        if len(args) > 0:
            # e.g. ``curio set``
            self['action'] = args[0]
        if len(args) > 1:
            # e.g. ``curio get entity:key``
            subargs = args[1].split(':')
            location = subargs[0].split('/')
            self['entity'] = location[-1]
            if len(location) > 1:
                self['db'] = location[-2]
            if len(location) > 2:
                self['root'] = os.path.join(*location[0:-2])
            if len(subargs) > 1:
                self['key'] = subargs[1]
        if len(args) > 2:
            self['value'] = args[2]
