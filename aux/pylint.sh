#!/bin/sh

auxdir=`dirname $0`
if [ -z $topdir ]; then
	topdir="."
fi
cd $auxdir
auxdir=`pwd`
cd ..
make >&2
topdir=`pwd`
cd build/lib.*

DISABLE_MSG="W0324,W0322,W0323,W0704,W0121,W0702"
IGNORE="^"
IGNORE="${IGNORE}\\(W0232\\|E0201\\):[^:]*:JID"
IGNORE="${IGNORE}\\|W0403:.*'stringprep'"
IGNORE="${IGNORE}\\|W0613:[^:]*:\\(StreamHandler.*'doc'\\|RR_.*\\('length'\\|'cls'\\)\\)"
IGNORE="${IGNORE}\\|W0613:[^:]*:\\(ClientStream.*'realm'\\|Client.*'iq'\\)"
IGNORE="${IGNORE}\\|W0613:[^:]*:\\(StreamBase.*'doc'\\)"
IGNORE="${IGNORE}\\|W0613:[^:]*:PlainClientAuthenticator.*\\('challenge'\\|'data'\\)"
IGNORE="${IGNORE}\\|W0613:[^:]*:PasswordManager.*\\('username'\\|'realm'\\|'acceptable_formats'\\)"
IGNORE="${IGNORE}\\|W0613:[^:]*:ClientAuthenticator.*\\('username'\\|'authzid'\\|'challenge'\\|'data'\\)"
IGNORE="${IGNORE}\\|W0613:[^:]*:ServerAuthenticator.*\\('initial_response'\\|'response'\\)"
IGNORE="${IGNORE}\\|W0613:[^:]*:DigestMD5ServerAuthenticator.start.*'response'"
IGNORE="${IGNORE}\\|W0613:[^:]*:MucRoomState.set_stream.*'stream'"
IGNORE="${IGNORE}\\|W0613:[^:]*:LegacyClientStream.*'\\(stanza\\|resource\\)'"
IGNORE="${IGNORE}\\|W0613:[^:]*:JabberClient\\.connect.*'register'"
IGNORE="${IGNORE}\\|W0612:[^:]*:\\(StreamBase._connect.*'canonname'\\|StreamBase._loop_iter.*'ofd'\\)"
IGNORE="${IGNORE}\\|W0612:[^:]*:\\(parse_message:.*'i'\\|do_query:.*'canonname'\\)"
IGNORE="${IGNORE}\\|W0201:[^:]*:\\([^.]*\\._reset\\|ClientStream.*'me'\\)"
IGNORE="${IGNORE}\\|W0201:[^:]*:StreamSASLMixIn.*'\\(me\\|authenticated\\|peer_authenticated\\|peer\\|auth_method_used\\)'"
IGNORE="${IGNORE}\\|W0201:[^:]*:StreamTLSMixIn.*'\\(socket\\|features\\)'"
IGNORE="${IGNORE}\\|W0201:[^:]*:ComponentStream._process_node"
IGNORE="${IGNORE}\\|W0221:[^:]*:\\(Client\\|Component\\)Stream._\\?\\(connect\\|accept\\)"

export PYLINTRC=$auxdir/pylintrc
if [ -n "$1" ] ; then
	pylint --disable-msg $DISABLE_MSG $1 | sed -e"s#$IGNORE#ignore that: &#"
else
	pylint --disable-msg $DISABLE_MSG pyxmpp | sed -e"s#$IGNORE#ignore that: &#"
fi
