.PHONY: test

test:
	nosetests curio/tests/ --with-coverage --cover-package curio
