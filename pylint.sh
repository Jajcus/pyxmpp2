#!/bin/sh

topdir=`dirname $0`
if [ -z $topdir ]; then
	topdir="."
fi
cd $topdir
topdir=`pwd`
cd build/lib.*

FLAGS="--disable-msg W0324,W0322,W0323"

export PYLINTRC=$topdir/pylintrc
if [ -n "$1" ] ; then
	pylint $FLAGS $1
else
	pylint $FLAGS pyxmpp
fi
