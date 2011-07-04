#
# (C) Copyright 2003-2011 Jacek Konieczny <jajcus@jajcus.net>
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

"""XMPP-IM roster handling.

Normative reference:
  - :RFC:`6121`
"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import logging

from collections import Mapping

from .etree import ElementTree
from .settings import XMPPSettings
from .jid import JID
from .iq import Iq
from .interfaces import XMPPFeatureHandler
from .interfaces import iq_set_stanza_handler
from .interfaces import StanzaPayload, payload_element_name
from .interfaces import EventHandler, event_handler, Event
from .streamevents import AuthorizedEvent
from .exceptions import BadRequestProtocolError, NotAcceptableProtocolError

logger = logging.getLogger("pyxmpp2.ext.version")

ROSTER_NS = u"jabber:iq:roster"
ROSTER_QNP = u"{{{0}}}".format(ROSTER_NS)
QUERY_TAG = ROSTER_QNP + u"query"
ITEM_TAG = ROSTER_QNP + u"item"
GROUP_TAG = ROSTER_QNP + u"group"
FEATURE_ROSTERVER = "{urn:xmpp:features:rosterver}ver"

class RosterReceivedEvent(Event):
    """Event emitted when roster is received from server.
    
    :Ivariables:
        - `roster_client`: roster client object that emitted this event
        - `roster`: the roster received
    :Types:
        - `roster_client`: `RosterClient`
        - `roster`: `Roster`
    """
    # pylint: disable=R0903
    def __init__(self, roster_client, roster):
        self.roster_client = roster_client
        self.roster = roster

    def __unicode__(self):
        return u"Roster received ({0} items)".format(len(self.roster))

class RosterUpdatedEvent(Event):
    """Event emitted when roster update is received.
    
    :Ivariables:
        - `roster_client`: roster client object that emitted this event
        - `item`: the update received
    :Types:
        - `roster_client`: `RosterClient`
        - `item`: `RosterItem`
    """
    # pylint: disable=R0903
    def __init__(self, roster_client, old_item, item):
        self.roster_client = roster_client
        self.old_item = old_item
        self.item = item

    def __unicode__(self):
        return u"Roster update received for: {0}".format(self.item.jid)

class RosterNotReceivedEvent(Event):
    """Event emitted when a roster request fails.
    
    :Ivariables:
        - `roster_client`: roster client object that emitted this event
        - `stanza`: the invalid or error stanza received, `None` in case of
          time-out.
    :Types:
        - `roster_client`: `RosterClient`
        - `stanza`: `Stanza`
    """
    # pylint: disable=R0903
    def __init__(self, roster_client, stanza):
        self.roster_client = roster_client
        self.stanza = stanza 

    def __unicode__(self):
        if self.stanza is None:
            return u"Roster fetch fail (timeout)"
        if self.stanza.stanza_type == u"error":
            cond = self.stanza.error.condition_name
            text = self.stanza.error.text
            if text:
                return u"Roster fetch fail: {0} ({1})".format(cond, text)
            else:
                return u"Roster fetch fail: {0}".format(cond)
        else:
            return u"Roster fetch fail: invalid response from server"

class RosterItem(object):
    """
    Roster item.

    Represents part of a roster, or roster update request.

    :Ivariables:
        - `jid`: the JID
        - `name`: visible name
        - `groups`: roster groups the item belongs to
        - `subscription`: subscription type (None, "to", "from", "both",
                                                                or "remove")
        - `ask`: "subscribe" if there was unreplied subsription request sent
        - `approved`: `True` if the entry subscription is pre-approved
    :Types:
        - `jid`: `JID`
        - `name`: `unicode`
        - `groups`: `set` of `unicode`
        - `subscription`: `unicode`
        - `ask`: `unicode`
        - `approved`: `bool`
    """
    def __init__(self, jid, name = None, groups = None,
                            subscription = None, ask = None, approved = None):
        """
        Initialize a roster item element.

        :Parameters:
            - `jid`: entry jid
            - `name`: item visible name
            - `groups`: iterable of groups the item is member of
            - `subscription`: subscription type (None, "to", "from", "both" 
                                                                    or "remove")
            - `ask`: "subscribe" if there was unreplied subscription request
              sent
            - `approved`: `True` if the entry subscription is pre-approved
        """
        # pylint: disable=R0913
        self.jid = JID(jid)
        if name is not None:
            self.name = unicode(name)
        else:
            self.name = None
        if groups is not None:
            self.groups = set(groups)
        else:
            self.groups = set()
        if subscription == u"none":
            subscription = None
        # no verify because of RFC 6121, section 2.1.2.5 (client MUST ignore...)
        self.subscription = subscription
        if ask is not None:
            self.ask = ask
        else:
            self.ask = None
        self.approved = bool(approved)
        self._duplicate_group = False

    @classmethod
    def from_xml(cls, element):
        """Make a RosterItem from an XML element.

        :Parameters:
            - `element`: the XML element
        :Types:
            - `element`: :etree:`ElementTree.Element`
        
        :return: a freshly created roster item
        :returntype: `cls`
        """
        if element.tag != ITEM_TAG:
            raise ValueError("{0!r} is not a roster item".format(element))
        try:
            jid = JID(element.get("jid"))
        except ValueError:
            raise BadRequestProtocolError(u"Bad item JID")
        subscription = element.get("subscription")
        ask = element.get("ask")
        name = element.get("name")
        duplicate_group = False
        groups = set()
        for child in element:
            if child.tag != GROUP_TAG:
                continue
            group = child.text
            if group is None:
                group = u""
            if group in groups:
                duplicate_group = True
            else:
                groups.add(group)
        approved = element.get("approved")
        if approved == "true":
            approved = True
        elif approved in ("false", None):
            approved = False
        else:
            logger.debug("RosterItem.from_xml: got unknown 'approved':"
                            " {0!r}, changing to False".format(approved))
            approved = False
        result = cls(jid, name, groups, subscription, ask, approved)
        result._duplicate_group = duplicate_group
        return result

    def as_xml(self, parent = None):
        """Make an XML element from self.

        :Parameters:
            - `parent`: Parent element
        :Types:
            - `parent`: :etree:`ElementTree.Element`
        """
        if parent:
            element = ElementTree.SubElement(parent, ITEM_TAG)
        else:
            element = ElementTree.Element(ITEM_TAG)
        element.set("jid", self.jid)
        element.set("name", self.name)
        element.set("subscription", self.subscription)
        if self.ask:
            element.set("ask", self.ask)
        if self.approved:
            element.set("approved", self.approved)
        for group in self.groups:
            ElementTree.SubElement(element, GROUP_TAG).text = group
        return element

    def _verify(self, valid_subscriptions, fix):
        """Check if `self` is valid roster item.

        Valid item must have proper `subscription` and valid value for 'ask'.

        :Parameters:
            - `valid_subscriptions`: sequence of valid subscription values
            - `fix`: if `True` than replace invalid 'subscription' and 'ask'
              values with the defaults
        :Types:
            - `fix`: `bool`

        :Raise: `ValueError` if the item is invalid.
        """
        if self.subscription not in valid_subscriptions:
            if fix:
                logger.debug("RosterItem.from_xml: got unknown 'subscription':"
                        " {0!r}, changing to None".format(self.subscription))
                self.subscription = None
            else:
                raise ValueError("Bad 'subscription'")
        if self.ask not in (None, u"subscribe"):
            if fix:
                logger.debug("RosterItem.from_xml: got unknown 'ask':"
                                " {0!r}, changing to None".format(self.ask))
                self.ask = None
            else:
                raise ValueError("Bad 'ask'")

    def verify_roster_result(self, fix = False):
        """Check if `self` is valid roster item.

        Valid item must have proper `subscription` value other than 'remove'
        and valid value for 'ask'.

        :Parameters:
            - `fix`: if `True` than replace invalid 'subscription' and 'ask'
              values with the defaults
        :Types:
            - `fix`: `bool`

        :Raise: `ValueError` if the item is invalid.
        """
        self._verify((None, u"from", u"to", u"both"), fix)

    def verify_roster_push(self, fix = False):
        """Check if `self` is valid roster push item.

        Valid item must have proper `subscription` value other and valid value
        for 'ask'.

        :Parameters:
            - `fix`: if `True` than replace invalid 'subscription' and 'ask'
              values with the defaults
        :Types:
            - `fix`: `bool`

        :Raise: `ValueError` if the item is invalid.
        """
        self._verify((None, u"from", u"to", u"both", u"remove"), fix)

    def verify_roster_set(self, fix = False, settings = None):
        """Check if `self` is valid roster set item.

        For use on server to validate incoming roster sets.

        Valid item must have proper `subscription` value other and valid value
        for 'ask'. The lengths of name and group names must fit the configured
        limits.

        :Parameters:
            - `fix`: if `True` than replace invalid 'subscription' and 'ask'
              values with right defaults
            - `settings`: settings object providing the name limits
        :Types:
            - `fix`: `bool`
            - `settings`: `XMPPSettings`

        :Raise: `BadRequestProtocolError` if the item is invalid.
        """
        # pylint: disable=R0912
        try:
            self._verify((None, u"remove"), fix)
        except ValueError, err:
            raise BadRequestProtocolError(unicode(err))
        if self.ask:
            if fix:
                self.ask = None
            else:
                raise BadRequestProtocolError("'ask' in roster set")
        if self.approved:
            if fix:
                self.approved = False
            else:
                raise BadRequestProtocolError("'approved' in roster set")
        if settings is None:
            settings = XMPPSettings()
        name_length_limit = settings["roster_name_length_limit"]
        if self.name and len(self.name) > name_length_limit:
            raise NotAcceptableProtocolError(u"Roster item name too long")
        group_length_limit = settings["roster_group_name_length_limit"]
        for group in self.groups:
            if not group:
                raise NotAcceptableProtocolError(u"Roster group name empty")
            if len(group) > group_length_limit:
                raise NotAcceptableProtocolError(u"Roster group name too long")
        if self._duplicate_group:
            raise BadRequestProtocolError(u"Item group duplicated")

    def __repr__(self):
        return "<RosterItem {0!r}>".format(unicode(self.jid))

@payload_element_name(QUERY_TAG)
class RosterPayload(StanzaPayload, Mapping):
    """<query/> element carried via a roster Iq stanza.
    
    Can contain a single item or whole roster with optional version 
    information.

    Works like a mapping from JIDs to roster items.

    :Ivariables:
        - `version`: the version attribute
        - `_items`: jid -> roster item dictionary
    :Types:
        - `_items`: `dict` of `JID` -> `RosterItem`
    """
    def __init__(self, items = None, version = None):
        """
        :Parameters:
            - `items`: sequence of roster items
            - `version`: optional roster version string
        :Types:
            - `items`: iterable
            - `version`: `unicode`
        """
        if items is not None:
            self._items = dict((item.jid, item) for item in items)
        else:
            self._items = {}
        self.version = version

    @classmethod
    def from_xml(cls, element):
        """
        Create a `RosterPayload` object from an XML element.

        :Parameters:
            - `element`: the XML element
        :Types:
            - `element`: :etree:`ElementTree.Element`
        
        :return: a freshly created roster payload
        :returntype: `cls`
        """
        # pylint: disable-msg=W0221
        items = []
        jids = set()
        if element.tag != QUERY_TAG:
            raise ValueError("{0!r} is not a roster item".format(element))
        version = element.get("ver")
        for child in element:
            if child.tag != ITEM_TAG:
                logger.debug("Unknown element in roster: {0!r}".format(child))
                continue
            item = RosterItem.from_xml(child)
            if item.jid in jids:
                logger.warning("Duplicate jid in roster: {0!r}".format(
                                                                    item.jid))
                continue
            jids.add(item.jid)
            items.append(item)
        return cls(items, version)

    def as_xml(self):
        """Return the XML representation of roster payload.

        Makes a <query/> element with <item/> children.
        """
        element = ElementTree.Element(QUERY_TAG)
        if self.version is not None:
            element.set("ver", self.version)
        for item in self._items.values():
            item.as_xml(element)
        return element
    
    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __contains__(self, jid):
        return jid in self._items

    def __getitem__(self, jid):
        return self._items[jid]

    def keys(self):
        """Return the JIDs in the roster.
        
        :Returntype: iterable of `JID`
        """
        return self._items.keys()

    def values(self):
        """Return the roster items.
        
        :Returntype: iterable of `RosterType`
        """
        return self._items.values()

class Roster(RosterPayload):
    """Represents the XMPP roster (contact list).

    Please note that changes to this object do not automatically affect
    any remote copy of the roster.
    """
    def __init__(self, items = None, version = None):
        if items:
            for item in items:
                if item.subscription == "remove":
                    raise ValueError("Roster item subscription cannot be"
                                                                " 'remove'")
        RosterPayload.__init__(self, items, version)

    @classmethod
    def from_xml(cls, element):
        try:
            return RosterPayload.from_xml(cls, element)
        except ValueError, err:
            raise BadRequestProtocolError(unicode(err))

    @property
    def groups(self):
        """Set of groups defined in the roster.

        :Return: the groups
        :ReturnType: `set` of `unicode`
        """
        groups = set()
        for item in self._items.values():
            groups |= item.groups
        return groups

    def get_items_by_name(self, name, case_sensitive = True):
        """
        Return a list of items with given name.

        :Parameters:
            - `name`: name to look-up
            - `case_sensitive`: if `False` the matching will be case
              insensitive.
        :Types:
            - `name`: `unicode`
            - `case_sensitive`: `bool`

        :Returntype: `list` of `RosterItem`
        """
        if not case_sensitive and name:
            name = name.lower()
        result = []
        for item in self._items.values():
            if item.name == name:
                result.append(item)
            elif item.name is None:
                continue
            elif not case_sensitive and item.name.lower() == name:
                result.append(item)
        return result

    def get_items_by_group(self, group, case_sensitive = True):
        """
        Return a list of items within a given group.

        :Parameters:
            - `name`: name to look-up
            - `case_sensitive`: if `False` the matching will be case
              insensitive.
        :Types:
            - `name`: `unicode`
            - `case_sensitive`: `bool`
        
        :Returntype: `list` of `RosterItem`
        """
        result = []
        if not group:
            for item in self._items.values():
                if not item.groups:
                    result.append(item)
            return result
        if not case_sensitive:
            group = group.lower()
        for item in self._items.values():
            if group in item.groups:
                result.append(item)
            elif not case_sensitive and group in [g.lower() for g 
                                                            in item.groups]:
                result.append(item)
        return result

    def add_item(self, item, replace = False):
        """
        Add an item to the roster.

        This will not automatically update the roster on the server.

        :Parameters:
            - `item`: the item to add
            - `replace`: if `True` then existing item will be replaced,
              otherwise a `ValueError` will be raised on conflict
        :Types:
            - `item`: `RosterItem`
            - `replace`: `bool`
        """
        if item.jid in self._items and not replace:
            raise ValueError("JID already in the roster")
        self._items[item.jid] = item

    def remove_item(self, jid):
        """Remove item from the roster.

        :Parameters:
            - `jid`: JID of the item to remove
        :Types:
            - `jid`: `JID`
        """
        del self._items[jid]

class RosterClient(XMPPFeatureHandler, EventHandler):
    """Client side implementation of the roster management (:RFC:`6121`,
    section 2.)
    """
    def __init__(self, settings = None):
        self.settings = settings if settings else XMPPSettings()
        self.roster = None
        self.server = None
        self.event_queue = self.settings["event_queue"]

    @event_handler(AuthorizedEvent)
    def handle_authorized_event(self, event):
        """Request roster upon login."""
        stream = event.stream
        self.server = event.authorized_jid.bare()
        versioning = False
        if stream and stream.features is not None:
            if stream.features.find(FEATURE_ROSTERVER) is not None:
                versioning = True
        if versioning:
            if self.roster is not None and self.roster.version is not None:
                version = self.roster.version
            else:
                version = u""
        else:
            version = None
        self.request_roster(version)

    def request_roster(self, version = None):
        """Request roster from server.

        :Parameters:
            - `version`: if not `None` versioned roster will be requested
              for given local version. Use "" to request full roster.
        :Types:
            - `version`: `unicode`
        """
        processor = self.stanza_processor
        request = Iq(stanza_type = "get")
        request.set_payload(RosterPayload(version = version))
        processor.set_response_handlers(request, 
                                    self._get_success, self._get_error)
        processor.send(request)

    def _get_success(self, stanza):
        """Handle successful response to the roster request.
        """
        payload = stanza.get_payload(RosterPayload)
        if not payload:
            logger.warning("Bad roster response")
            self.event_queue.put(RosterNotReceivedEvent(self, stanza))
            return
        items = list(payload.values())
        for item in items:
            item.verify_roster_result(True)
        self.roster = Roster(items, payload.version)
        self.event_queue.put(RosterReceivedEvent(self, self.roster))

    def _get_error(self, stanza):
        """Handle failure of the roster request.
        """
        if stanza:
            logger.warning(u"Roster request failed: {0}".format(
                                                stanza.error.condition_name))
        else:
            logger.warning(u"Roster request failed: timeout")
        self.event_queue.put(RosterNotReceivedEvent(self, stanza))

    @iq_set_stanza_handler(RosterPayload)
    def handle_roster_push(self, stanza):
        """Handle a roster push received from server.
        """
        if self.server is None and stanza.from_jid:
            logger.debug(u"Server address not known, cannot verify roster push"
                                " from {0}".format(stanza.from_jid))
            return stanza.make_error_response(u"service-unavailable")
        if self.server and stanza.from_jid and stanza.from_jid != self.server:
            logger.debug(u"Roster push from invalid source: {0}".format(
                                                            stanza.from_jid))
            return stanza.make_error_response(u"service-unavailable")
        payload = stanza.get_payload(RosterPayload)
        if len(payload) != 1:
            logger.warning("Bad roster push received ({0} items)"
                                                    .format(len(payload)))
            return stanza.make_error_response(u"bad-request")
        if self.roster is None:
            logger.debug("Dropping roster push - no roster here")
            return True
        item = payload.values()[0]
        item.verify_roster_push(True)
        old_item = self.roster.get(item.jid)
        if item.subscription == "remove":
            if old_item:
                self.roster.remove_item(item.jid)
        else:
            self.roster.add_item(item, replace = True)
        self.event_queue.put(RosterUpdatedEvent(self, old_item, item))
        return stanza.make_result_response()

XMPPSettings.add_setting(u"roster_name_length_limit", type = int,
        default = 1023,
        doc = u"""Maximum length of roster item name."""
    )
XMPPSettings.add_setting(u"roster_group_name_length_limit", type = int,
        default = 1023,
        doc = u"""Maximum length of roster group name."""
    )
