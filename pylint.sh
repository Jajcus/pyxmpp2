#!/bin/sh

topdir=`dirname $0`
if [ -z $topdir ]; then
	topdir="."
fi
cd $topdir
make >&2
topdir=`pwd`
cd build/lib.*

DISABLE_MSG="W0324,W0322,W0323,W0704,W0121,W0702"
IGNORE="^"
IGNORE="${IGNORE}\\(W0232\\|E0201\\):[^:]*:JID"
IGNORE="${IGNORE}\\|W0403:.*'stringprep'"
IGNORE="${IGNORE}\\|W0613:[^:]*:\\(StreamHandler.*'doc'\\|RR_.*\\('length'\\|'cls'\\)\\)"
IGNORE="${IGNORE}\\|W0613:[^:]*:\\(ClientStream.*'realm'\\|Client.*'iq'\\)"
IGNORE="${IGNORE}\\|W0612:[^:]*:\\(parse_message:.*'i'\\|do_query:.*'canonname'\\)"
IGNORE="${IGNORE}\\|W0201:[^:]*:\\(.*\\._reset:\\|ClientStream.*'me'\\)"
IGNORE="${IGNORE}\\|W0221:[^:]*:ClientStream._\\?\\(connect\\|accept\\)"

export PYLINTRC=$topdir/pylintrc
if [ -n "$1" ] ; then
	pylint --disable-msg $DISABLE_MSG $1 | sed -e"s#$IGNORE#ignore that: &#"
else
	pylint --disable-msg $DISABLE_MSG pyxmpp | sed -e"s#$IGNORE#ignore that: &#"
fi
