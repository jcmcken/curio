
from optparse import OptionParser
import os
import re
from curio.core import CurioManager, CurioConfig
from curio.exceptions import CurioLocked, UnsetKey

CONFIG_DEFAULTS = {
    'root': '/var/lib/curio', # where curio should look for databases
    'db': None, # which database in ``root`` to use    
    'entity': None, # which entity to examine
    'key': None, # which key to examine
    'value': None # the value to set
}
ENV_MAPPING = {
    'root': 'CURIO_ROOT',
    'db': 'CURIO_DB',
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

def get_cli():
    usage = 'Usage: %prog [options] <action> <uri> [extra_arguments]'
    epilog = (
    "Valid actions:\n"
    "%s" % ", ".join(VALID_ACTIONS)
    )
    cli = OptionParser(usage=usage, epilog=epilog)
    cli.add_option('-s', '--settings', action='store_true', help="print current curio settings (without executing any actions)")
    return cli

def print_config_settings(config):
    ordering = config.keys()
    ordering.sort()
    for key in ordering:
        print "%s = %s" % (key, config[key])

def main(args=None):

    cli = get_cli()
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
