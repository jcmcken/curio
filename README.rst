============
Introduction
============

**Curio** is a simple, command-line driven key-value store, perfect for scripts or
microapps that need to store a small to fair amount of unstructured data, but don't 
really need or want a fully-fledged NoSQL solution such as Cassandra, HBase, Redis, etc.

Data Structures
---------------

**Curio** data structures can be summarized in the following way:

* A database has multiple entities
* An entity has multiple keys
* Each entity key has one associated value

This is the 'column family' approach to key-value storage, and can be visualized as a nested hash map::

    {'database':
        'entity1': {
            'key1': 'value1',
            'key2': 'value2'
        },
        'entity2': {
            'key1': 'value1'
        }
    }

Both entity and key names are expected to:

* Start with an alphanumeric character
* Only contain alphanumeric characters, underscores, periods, and dashes

You will get an 'invalid name' error if you try to use a name that violates these rules.

Concurrency
-----------

**Curio** utilizes cross-process, entity-level write locking. In other words, if one process attempts to set an entity key at the same time as another process, it will be locked out until the first process is done.

Remember, the ``curio`` datastore is not meant to be a fully-fledged NoSQL solution, but is only intended for small applications and scripts. For those use cases, this level of concurrency should be more than adequate. 

Security
--------

Discretionary access controls (e.g. UNIX file permissions) are the easiest way to secure ``curio`` data. **Curio** will write all data with a umask of ``0027`` by default (configurable with the ``CURIO_UMASK`` environmental variable). So by default, only the user who creates the database should be able to read or write to it. 

Encrypted data can be implemented fairly easily, whether through the command line or the Python API. 

For example::

    $ DATA=`echo "some data" | openssl aes-256-cbc -encrypt -base64` 
    enter aes-256-cbc encryption password:
    Verifying - enter aes-256-cbc encryption password:
    $ curio set some_entity:some_key "$DATA"

Note that ``curio`` utilizes Python's ``pickle`` serialization format as its backend storage format.

Using the CLI
-------------

Addressing Data
###############

The best way (in my opinion) to work with ``curio`` data is to utilize the built-in ``CURIO_ROOT`` and ``CURIO_DB`` environmental variables::

    $ export CURIO_ROOT=.
    $ export CURIO_DB="test_db"
    $ curio find
    $ curio set some_entity:some_key some_val

Alternatively, you can specify the full resource target::

    $ curio find ./test_db/

If the full target is given, this is how ``curio`` interprets it::

    [root_directory]/[database]/[entity]:[key] [value]

For example, to get a key::

    $ curio get ./test_db/entity:some_key

Note that using the full target requires both the root directory and the database to be specified. This can be prone to error, which is why I recommend using the environmental variables.

Actions
#######

Get
+++

Retrieve the value of a specific key from a specific entity and print it to STDOUT. 

When retrieving a key that has not yet been set, ``curio`` will exit with a return code of 1 and print the text ``<unset>`` to STDOUT. 

Retrieve a key that's previous been set::

    $ curio get some_entity:some_key
    some_val

Retrieving an unset key::

    $ curio get some_entity:unset_key
    <unset>


Find
++++

Search all entities that match a regular expression. Search all keys that match a regular expression. Search in combination. If there are results, print the entity names and all matching keys with their values.

If no entity or no key expression is provided, then ``.*`` (i.e. match all) is assumed.

Print the entire database::

    $ curio find

Search all entities whose names start with ``foo``::

    $ curio find ^foo

Search the same entities, but only list keys that end in ``bar``::

    $ curio find ^foo:bar$

Find all keys that end in ``bar``::

    $ curio find '.*:bar$'

Set
+++

Set the value of a specific key in a specific entity.

This will overwrite the contents of the given key if it already has a value::

    $ curio set some_entity:some_key some_val

Delete
++++++

Delete the key-value pair from the given entity. 

If it's the last key in that entity, the entity will be removed (i.e. will no longer show up in ``find`` results)::
 
    $ curio del some_entity:some_key


Using the Library
-----------------

There are two ways to use ``curio`` from Python: You can either manipulate a ``curio`` database using a manager (this is very similar to the CLI), or you can operate at a lower level and work against the raw dictionaries, entity targets, etc. 

The second method is obviously much more prone to error.

Using the Manager
#################

To use the manager, simply create a ``CurioManager`` object and pass it the directory of a ``curio`` database::

    from curio.core import CurioManager

    manager = CurioManager('/path/to/db')

Now you can execute the standard actions::

    manager.set('some_entity', 'some_key', 'some_val')
    value = manager.get('some_entity', 'some_key')
    results_dict = manager.find(r'^foo', r'bar$')
    results_dict2 = manager.find(r'^foo')
    manager.delete('some_entity', 'some_key')

Changes to a ``curio`` database using the manager are written to disk as the action is called. There is no concept of a transaction.

Without Using the Manager
#########################

I will leave this as an exercise for the reader. Remember, ``curio`` is meant to be a very simple datastore for small applications and scripts. If you need to spend time hacking around with the backend, you might as well use an actual NoSQL server that has more robust and fully-fledged features and API. 
