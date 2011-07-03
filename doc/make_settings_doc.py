#!/usr/bin/python

from glob import glob
import codecs

import pyxmpp2
from pyxmpp2.settings import XMPPSettings

def import_modules():
    base = pyxmpp2.__path__[0]
    for filename in glob(base + "/*.py") + glob(base + "/*/*.py"):
        try:
            module_name = "pyxmpp2" + filename[len(base):-3].replace("/", ".")
            __import__(module_name)
        except ImportError:
            pass

def type_string(type_spec):
    if isinstance(type_spec, basestring):
        return type_spec
    try:
        if type_spec.__module__ == '__builtin__':
            return u"``{0}``".format(type_spec.__name__)
        if hasattr(type_spec, "im_class"):
            klass = type_spec.im_class
            type_name = u".".join((klass.__module__, klass.__name__,
                                                        type_spec.__name__))
        else:
            type_name = u".".join((type_spec.__module__, type_spec.__name__))
        if type_name.startswith(u"pyxmpp2."):
            return u"`{0}`".format(type_name)
        else:
            return u":std:`{0}`".format(type_name)
    except AttributeError:
        return u"`{0}`".format(type_spec.__name__)

def default_string(setting):
    if setting.default_d:
        return setting.default_d
    if setting.default is not None:
        default = setting.default
    elif setting.factory:
        default = setting.factory(XMPPSettings())
    else:
        return u"``None``"
    return u"``{0!r}``".format(default)

def cmdline_string(setting):
    option = setting.name.replace("_", "-")
    if setting.type is bool:
        return "--{0} | --no-{0}".format(option)
    else:
        return "--{0} {1}".format(option, setting.name.upper())

def dump_settings_group(doc, index, settings):
    for setting in settings:
        print >> doc
        #print >> doc, u".. _{0}:".format(setting.name)
        #print >> doc
        print >> doc, setting.name
        print >> doc, u"." * len(setting.name)
        print >> doc
        print >> doc, u"  * Type: {0}".format(type_string(setting.type))
        print >> doc, u"  * Default: {0}".format(default_string(setting))
        if setting.cmdline_help:
            print >> doc, u"  * Command line: ``{0}``".format(cmdline_string(
                                                                    setting))
        print >> doc
        print >> doc, setting.doc
        print >> index, u'{0} setting\t#{1}'.format(
                        setting.name, setting.name.replace("_", "-"))

def dump_settings(doc, index):
    basic_settings = [ x for x in XMPPSettings._defs.values() if x.basic ]
    basic_settings = sorted(basic_settings, key = lambda x: x.name)
    extra_settings = [ x for x in XMPPSettings._defs.values() if not x.basic ]
    extra_settings = sorted(extra_settings, key = lambda x: x.name)

    print >> index, "settings list\t#"

    print >> doc, ".. default-role:: pyxmpp2"
    print >> doc
    print >> doc, "PyXMPP2 Settings"
    print >> doc, "================"
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

