#!/usr/bin/python

from glob import glob
import codecs

import pyxmpp2
from pyxmpp2.settings import XMPPSettings

def import_modules():
    base = pyxmpp2.__path__[0]
    for filename in glob(base + "/*.py") + glob(base + "/mainloop/*.py"):
        try:
            module_name = "pyxmpp2" + filename[len(base):-3].replace("/", ".")
            __import__(module_name)
        except ImportError:
            pass

def dump_settings_group(doc, index, settings):
    for setting in settings:
        print >> doc
        print >> doc, setting.name
        print >> doc, u"." * len(setting.name)
        print >> doc
        if isinstance(setting.type, basestring):
            print >> doc, u"  * Type: {0}".format(setting.type)
        elif setting.type is not None:
            print >> doc, u"  * Type: ``{0}``".format(setting.type.__name__)
        if setting.default_d:
            default = setting.default_d
        elif setting.default is not None:
            default = repr(setting.default)
        elif setting.factory:
            default = repr(setting.factory(XMPPSettings()))
        else:
            default = u'None'
        print >> doc, u"  * Default: ``{0}``".format(default)
        print >> doc
        print >> doc, setting.doc
        print >> index, u'{0} setting\t#{0}'.format(setting.name)

def dump_settings(doc, index):
    basic_settings = [ x for x in XMPPSettings._defs.values() if x.basic ]
    basic_settings = sorted(basic_settings, key = lambda x: x.name)
    extra_settings = [ x for x in XMPPSettings._defs.values() if not x.basic ]
    extra_settings = sorted(extra_settings, key = lambda x: x.name)

    print >> index, "settings list\t#"

    print >> doc, "PyXMPP2 Settings"
    print >> doc, "==============="
    print >> doc
    print >> doc, u"Basic Settings"
    print >> doc, u"--------------"
    print >> doc
    print >> doc, u"It is recommended these settings can be configured by the"
    print >> doc, u"end user, as they may be required for correct operation with"
    print >> doc, u"a specific service"
    dump_settings_group(doc, index, basic_settings)

    print >> doc
    print >> doc, u"Extra Settings"
    print >> doc, u"--------------"
    print >> doc
    print >> doc, u"These settings can even further change the PyXMPP"
    print >> doc, u" behaviour, but in most cases there is no need to set them."
    dump_settings_group(doc, index, extra_settings)

if __name__ == "__main__":
    import_modules()
    with codecs.open("Settings.rst", "w", encoding = "utf-8") as doc:
        with codecs.open("settings.txt", "w", encoding = "utf-8") as index:
            dump_settings(doc, index)

