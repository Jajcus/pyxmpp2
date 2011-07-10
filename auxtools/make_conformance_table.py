#!/usr/bin/python

"""Fetch an XMPP RFC and build a reStructuredText table with the
conformance features sets"""

import argparse
import re
import textwrap
import itertools

from urlparse import urljoin

from lxml import etree
from lxml import html

ROLES_RE = re.compile(r"Client ([^.,]*), Server ([^.,]*)|Both ([^.,]*)")


class Feature(object):
    def __init__(self, name, descr, url, client, server):
        self.name = name
        self.descr = descr
        self.url = url
        self.client = client
        self.server = server

    @classmethod
    def from_element(cls, element, base_url):
        r = element.xpath("dt[text()='Feature:']/following-sibling::dd[1]")
        name = r[0].text.strip()
        r = element.xpath("dt[text()='Description:']/following-sibling::dd[1]")
        descr = r[0].text.strip()
        r = element.xpath("dt[text()='Section:']/following-sibling::dd[1]/a")
        url = urljoin(base_url, r[0].get("href"))
        r = element.xpath("dt[text()='Roles:']/following-sibling::dd[1]")
        match = ROLES_RE.match(r[0].text)
        if match.group(3):
            client = match.group(3)
            server = match.group(3)
        else:
            client = match.group(1)
            server = match.group(2)
        return cls(name, descr, url, client, server)

    def __unicode__(self):
        return u"""Feature: {0.name}
Description: {0.descr}
URL: {0.url}
Client: {0.client}
Server: {0.server}
""".format(self)

def print_grid_table(features, add_notes = False):
    feature_width = 10
    descr_width = 40
    role_width = 6
    for feature in features:
        if len(feature.name) + 3 > feature_width:
            feature_width = len(feature.name) + 3


    rule = ("+" + (feature_width + 2) * "-" + "+" + (descr_width + 2) * "-" +
            "+" + (role_width + 2) * "-" + "+" + (role_width + 2) * "-" + "+")
    print
    print rule
    print u"| {0} | {1} | {2} | {3} |".format("Feature".ljust(feature_width),
            "Description".ljust(descr_width), "Client".ljust(role_width),
            "Server".ljust(role_width)).encode("utf-8")
    print rule.replace("-", "=")
    for feature in features:
        name_l = [ "`{0}`_".format(feature.name) ]
        desc_l = textwrap.wrap(feature.descr, descr_width)

        height = max(len(name_l), len(desc_l))
        name_i = itertools.chain(name_l, itertools.repeat(u""))
        desc_i = itertools.chain(desc_l, itertools.repeat(u""))
        client_i = itertools.chain([feature.client], itertools.repeat(u""))
        server_i = itertools.chain([feature.server], itertools.repeat(u""))
       
        for i in xrange(height):
            print u"| {0} | {1} | {2} | {3} |".format(
                    name_i.next().ljust(feature_width),
                    desc_i.next().ljust(descr_width),
                    client_i.next().ljust(role_width),
                    server_i.next().ljust(role_width)).encode("utf-8")
        print rule
    print

def print_list_table(features, add_notes = False):
    print
    print ".. list-table::"
    print "   :widths: 10 40 8 8 34"
    print "   :header-rows: 1"
    print 
    print "   * - Feature"
    print "     - Description"
    print "     - Client"
    print "     - Server"
    if add_notes:
        print "     - Notes"
    for feature in features:
        print u"   * - `{0}`_".format(feature.name).encode("utf-8")
        print u"     - {0}".format(feature.descr).encode("utf-8")
        print u"     - {0}".format(feature.client).encode("utf-8")
        print u"     - {0}".format(feature.server).encode("utf-8")
        if add_notes:
            print "     - "
    print


def main():
    arg_parser = argparse.ArgumentParser(
                                    description = 'Conformance table builder')
    arg_parser.add_argument('rfc', help = "RFC number or URL"
                                            " (the xmpp.org HTML RFCs only)")
    arg_parser.add_argument('--list', help = "Use list format",
                    action = 'store_const', const = 'list', dest = 'mode',
                    default = 'grid')
    arg_parser.add_argument('--blank', help = "Leave empty 'role' fields",
                                                        action = 'store_true')
    arg_parser.add_argument('--notes', help = "Add a 'notes' column",
                                                        action = 'store_true')
    args = arg_parser.parse_args()
    try:
        int(args.rfc)
        rfc_url = "http://xmpp.org/rfcs/rfc{0}.html".format(args.rfc)
    except ValueError:
        rfc_url = args.rfc

    tree = html.parse(rfc_url)
    feature_elements = tree.xpath("//dl[dt='Feature:']")
    features = [Feature.from_element(e, rfc_url) for e in feature_elements]

    if args.blank:
        for feature in features:
            if feature.client != "N/A":
                feature.client = ""
            if feature.server != "N/A":
                feature.server = ""

    if args.mode == "list":
        print_list_table(features, args.notes)
    else:
        print_grid_table(features, args.notes)

    for feature in features:
        print u".. _{0}: {1}".format(feature.name, feature.url)

if __name__ == "__main__":
    main()
