#!/bin/sh

topdir=`dirname $0`
if [ -z $topdir ]; then
	topdir="."
fi
cd $topdir
topdir=`pwd`
cd build/lib.*

DISABLE_MSG="W0324,W0322,W0323,W0704,W0121,W0702"
IGNORE="^\\(W0232\\|E0201\\):[^:]*:JID"

export PYLINTRC=$topdir/pylintrc
if [ -n "$1" ] ; then
	pylint --disable-msg $DISABLE_MSG $1 | sed -e"s#$IGNORE#ignore that: &#"
else
	pylint --disable-msg $DISABLE_MSG pyxmpp | sed -e"s#$IGNORE#ignore that: &#"
fi
