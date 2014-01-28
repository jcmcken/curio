
from optparse import OptionParser
import os
import re
from curio.core import CurioManager, CurioConfig
from curio.exceptions import CurioLocked

class InvalidCurioPath(ValueError): pass

CONFIG_DEFAULTS = {
    'root': '/var/lib/curio', # where curio should look for databases
    'db': None, # which database in ``root`` to use    
    'entity': None, # which entity to examine
    'key': None, # which key to examine
    'value': None, # the value to set
    'umask': '0027',
}
ENV_MAPPING = {
    'root': 'CURIO_ROOT',
    'db': 'CURIO_DB',
    'umask': 'CURIO_UMASK',
}
VALID_ACTIONS = [ 'get', 'set', 'delete', 'find' ]
VALID_NAME = re.compile(r'^[A-Za-z0-9][\w\-\.]*$')
REQUIRED_OPTIONS = {
    'get': ['entity', 'key'],
    'set': ['entity', 'key', 'value'],
    'delete': ['entity', 'key'],
    'find': [],
}
REQUIRED_NAMELIKE = {
    'get': ['entity', 'key'],
    'set': ['entity', 'key'],
    'delete': ['entity', 'key'],
    'find': [],
}
DEFAULT_CONFIG_FILE = os.path.expanduser('~/.curio')

def create_parser():
    usage = 'Usage: %prog [options] <action> <uri> [extra_arguments]'
    epilog = (
    "Valid actions:\n"
    "%s" % ", ".join(VALID_ACTIONS)
    )
    cli = OptionParser(usage=usage, epilog=epilog)
    cli.add_option('-c', '--config', default=DEFAULT_CONFIG_FILE,
        help='Specify a config file to use (defaults to ~/.curio)')
    cli.add_option('-s', '--settings', action='store_true', 
        help="print current curio settings (without executing any actions)")
    return cli

def print_config_settings(config):
    ordering = config.keys()
    ordering.sort()
    for key in ordering:
        print "%s = %s" % (key, config[key])

class CurioCLI(object):
    VALID_ACTIONS = [ 'get', 'set', 'delete', 'find' ]

    def __init__(self):
        self._parser = create_parser()

    def run(self, argv=None):
        opts, args = self._cli.parse_args(argv)
        
        self._exit_on_noop(opts, args)
        self._exit_if_no_config(opts)

        config = CurioConfig(config_file=opts.config)

        if opts.settings:
            config.print_to_screen()
            raise SystemExit

        action, entity, key, value = self._parse_action_data(args)
        action_name = self._route_action(action)

        manager = CurioManager(config.uri)
        result = self._apply_action(manager, action_name, entity, key, value)

        self._display_result(result)

    def _display_result(self, action, result):
        # if write operation, or if get returns nothing
        if action in ['delete', 'set'] or (action == 'get' and result == None): 
            pass # no op
        elif action == 'get':
            print result
        elif action == 'find':
            self._display_entity_result(result)

    def _display_entity_result(self, result):
        for entity, data in result.iteritems():
            if data:
                print entity
            for key, value in data.iteritems():
                print "    %s = %s" % (key, value)

    def _apply_action(self, manager, action, entity, key, value=None):
        action_func = getattr(manager, action)

        # common args
        args = [entity, key]

        # ``set``-specific arg
        if action == 'set':
            args.append(value)
    
        # apply action
        result = action_func(*args)

        return result

    def _parse_action_data(self, args):
        action, entity, key, value = None, None, None, None
        if len(args) > 0:
            action = args.pop(0)
        if len(args) > 0:
            path_data = args.pop(0)
            entity, key = self._resolve_key_path(path_data)
        if len(args) > 0:
            value = args.pop(0)
        return action, entity, key, value 

    def _match_action(self, action):
        matches = [ i for i in self.VALID_ACTIONS if i.startswith(action) ]
        if not matches:
            raise RuntimeError, "invalid action '%s'" % action
        elif len(matches) > 1:
            raise RuntimeError, "vague action request, did you mean one of these -- %s -- ?" % ', '.join(matches)
        return matches[0]

    def _route_action(self, action):
        try:
            action = self._match_action(action)
        except RuntimeError, e:
            self._parser.error(e.args[0])
        return action

    def _exit_if_no_config(self, opts):
        if not os.path.isfile(opts.config):
            self._parser.error('no such file "%s"' % opts.config)

    def _exit_on_noop(self, opts, args):
        if not (opts.settings or args):
            self._parser.print_help()
            self._parser.exit(-1)

    def _resolve_key_path(self, path):
        try:
            entity, key = path.split(':', 1)
        except ValueError, e:
            raise InvalidCurioPath(path)
        return entity, key


def main(args=None):

    cli = create_parser()
    opts, args = cli.parse_args(args)
    if not reduce(lambda x,y: x or y, opts.__dict__.values()) and not args:
        cli.print_help()
        cli.exit(-1)

    config = CurioConfig(defaults=CONFIG_DEFAULTS)
    config.update_from_env(ENV_MAPPING)
    config.update_from_opts(opts)
    config.update_from_args(args)
    
    # validate that an action is supplied
    if not config.get('action'):
        cli.error("an action (%s) is required" % ', '.join(VALID_ACTIONS))
    
    try:
        action = config['action'] = route_action(config['action'])
    except RuntimeError, e:
        cli.error(e.args[0])
    
    if opts.settings:
        print_config_settings(config)
        raise SystemExit

    # validate all configs and options 
    validate_settings(cli, config, action)
    validate_names(cli, config, action)
    # validate root directory
    if not os.path.isdir(config['root']):
        cli.error("invalid root, no such directory: '%s'" % config['root'])

    # set the umask
    try:
        os.umask(int(config['umask'], 8))
    except ValueError:
        cli.error("invalid umask '%s'" % config['umask'])

    # now set up a manager to apply the action
    database_uri = os.path.join(config['root'], config['db'])
    manager = CurioManager(database_uri)
    action_func = getattr(manager, action)
    # common args
    args = map(config.get, ['entity', 'key'])
    # this action has an extra arg
    if action in ['set']:
        args.append(config.get('value'))

    # apply action
    try:
        results = action_func(*args)
    except UnsetKey, e:
        raise SystemExit, '<unset>'

    # if results to display, display 'em
    display_results(results, action)


def display_results(results, action):
    if action in ['delete', 'set']: # write ops, nothing to display
        pass # no op
    if action == 'get':
        print results
    elif action == 'find':
        for entity, data in results.iteritems():
            if data:
                print entity
            for key, value in data.iteritems():
                print "    %s = %s" % (key, value)

def route_action(action):
    matches = [ i for i in VALID_ACTIONS if i.startswith(action) ]
    if not matches:
        raise RuntimeError, "invalid action '%s'" % action
    elif len(matches) > 1:
        raise RuntimeError, "vague action request, did you mean one of these -- %s -- ?" % ', '.join(matches)
    return matches[0]

def validate_settings(cli, config, action):
    # validate required options
    for key in ['root', 'db'] + REQUIRED_OPTIONS[action]:
        env_var = ENV_MAPPING.get(key)
        msg = '%s is required' % key
        if env_var:
            msg += ' (environment variable %s)' % env_var
        if not config.get(key):
            cli.error(msg)

def validate_names(cli, config, action):
    # check valid values for various config opts
    for key in ['db'] + REQUIRED_NAMELIKE[action]:
        val = config.get(key)
        if not val: continue
        if not VALID_NAME.match(val):
            cli.error("invalid name for %s: '%s'" % (key, val))
