all:
	python setup.py build
	cd examples && ln -sf ../build/lib*/pyxmpp .
