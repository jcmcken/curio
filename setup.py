from distutils.core import setup

setup(
    name='curio',
    version='0.1',
    description='A simple, serverless, schemaless file-based key-value store',
    long_description="""
Curio is a simple, command-line driven key-value store, perfect for scripts or
microapps that need to store a small to fair amount of unstructured data, but don't 
really need or want a fully-fledged NoSQL solution such as Cassandra, HBase, Redis, etc.
""",
    author='Jon McKenzie',
    author_email='jcmcken@gmail.com',
    url='http://github.com/jcmcken/curio',
    scripts=['bin/curio'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.3',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: Database',
        'Topic :: Utilities',
    ],
    packages=['curio'],
    license='BSD',
    requires=['distutils']
)
