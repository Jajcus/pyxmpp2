#
# (C) Copyright 2005 Jacek Konieczny <jajcus@jajcus.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version
# 2.1 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
"""Simple API for simple things like sendig messages or single stanzas."""

__revision__="$Id: client.py 528 2005-01-20 21:14:53Z jajcus $"
__docformat__="restructuredtext en"

def xmpp_do(jid,password,function,server=None,port=None):
    """Connect as client to a Jabber/XMPP server and call the provided
    function when stream is ready for IM. The function will be called
    with one argument -- the XMPP stream. After function returns the stream is
    closed."""
    from pyxmpp.jabber.client import JabberClient
    class Client(JabberClient):
        def session_started(self):
            function(self.stream)
            self.disconnect()
    c=Client(jid,password,server=server,port=port)
    c.connect()
    try:
        c.loop(1)
    except KeyboardInterrupt:
        print u"disconnecting..."
        c.disconnect()

def send_message(my_jid,my_password,to_jid, body, subject=None,
        message_type=None,server=None,port=None):
    from pyxmpp.message import Message
    msg=Message(to_jid=to_jid,body=body,subject=subject,stanza_type=message_type)
    def fun(stream):
        stream.send(msg)
    xmpp_do(my_jid,my_password,fun,server,port)

# vi: sts=4 et sw=4
