#!/usr/bin/python


import os,sys

def main(module_list):
    options = {'target':None, 'modules':list(module_list), 'verbosity':1,
               'prj_name':'', 'action':'html', 'tests':{'basic':1},
               'show_imports':0, 'frames':1, 'private':None,
               'list_classes_separately': 0, 'debug':0,
               'docformat':None, 'top':None, 'inheritance': None,
               'ignore_param_mismatch': 0, 'alphabetical': 1}


    modules=_import(options['modules'],1)

    # Record the order of the modules in options.
    from epydoc.uid import make_uid
    muids = []
    for m in modules:
        try:
            muids.append(make_uid(m))
        except:
            raise
            if sys.stderr.softspace: print >>sys.stderr
            print >>sys.stderr, 'Failed to create a UID for %s' % m

    # Build their documentation
    docmap = _make_docmap(modules, options)
    f=Formatter(docmap)
    print f.format(module_list)

def escape(s):
    return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;').replace("'",'&apos;')

class _Progress:
    """

    The progress meter that is used by C{cli} to report its progress.
    It prints the status to C{stderrr}.  Depending on the verbosity,
    setting it will produce different outputs.

    To update the progress meter, call C{report} with the name of the
    object that is about to be processed.
    """
    def __init__(self, action, verbosity, total_items, html_file=0):
        """
        Create a new progress meter.

        @param action: A string indicating what action is performed on
            each objcet.  Examples are C{"writing"} and C{"building
            docs for"}.
        @param verbosity: The verbosity level.  This controls what the
            progress meter output looks like.
        @param total_items: The total number of items that will be
            processed with this progress meter.  This is used to let
            the user know how much progress epydoc has made.
        @param html_file: Whether to assume that arguments are html
            file names, and munge them appropriately.
        """
        self._action = action
        self._verbosity = verbosity
        self._total_items = total_items
        self._item_num = 1
        self._html_file = 0

    def report(self, argument):
        """
        Update the progress meter.
        @param argument: The object that is about to be processed.
        """
        if self._verbosity <= 0: return

        if self._verbosity==1:
            if self._item_num == 1 and self._total_items <= 70:
                sys.stderr.write('  [')
            if (self._item_num % 60) == 1 and self._total_items > 70:
                sys.stderr.write('  [%3d%%] ' %
                                 (100.0*self._item_num/self._total_items))
            sys.stderr.write('.')
            sys.stderr.softspace = 1
            if (self._item_num % 60) == 0 and self._total_items > 70:
                print >>sys.stderr
            if self._item_num == self._total_items:
                if self._total_items <= 70: sys.stderr.write(']')
                print >>sys.stderr
        elif self._verbosity>1:
            TRACE_FORMAT = (('  [%%%dd/%d]' % (len(`self._total_items`),
                                               self._total_items))+
                            ' %s %%s' % self._action)

            if self._html_file:
                (dir, file) = os.path.split(argument)
                (root, d) = os.path.split(dir)
                if d in ('public', 'private'):
                    argument = os.path.join(d, file)
                else:
                    fname = argument

            print >>sys.stderr, TRACE_FORMAT % (self._item_num, argument)
        self._item_num += 1


def _import(module_names, verbosity):
    """
    @return: A list of the modules contained in the given files.
        Duplicates are removed.  Order is preserved.
    @rtype: C{list} of C{module}
    @param module_names: The list of module filenames.
    @type module_names: C{list} of C{string}
    @param verbosity: Verbosity level for tracing output.
    @type verbosity: C{int}
    """
    from epydoc.imports import import_module, find_modules

    # First, expand packages.
    for name in module_names[:]:
        if os.path.isdir(name):
            # In-place replacement.
            index = module_names.index(name)
            new_modules = find_modules(name)
            if new_modules:
                module_names[index:index+1] = new_modules
            elif verbosity >= 0:
                if sys.stderr.softspace: print >>sys.stderr
                print  >>sys.stderr, 'Error: %r is not a pacakge' % name

    if verbosity > 0:
        print >>sys.stderr, 'Importing %s modules.' % len(module_names)
    modules = []
    progress = _Progress('Importing', verbosity, len(module_names))

    for name in module_names:
        progress.report(name)
        # Import the module, and add it to the list.
        try:
            module = import_module(name)
            if module not in modules: modules.append(module)
            elif verbosity > 2:
                if sys.stderr.softspace: print >>sys.stderr
                print >>sys.stderr, '  (duplicate)'
        except ImportError, e:
            if verbosity >= 0:
                if sys.stderr.softspace: print >>sys.stderr
                print  >>sys.stderr, e

    if len(modules) == 0:
        print >>sys.stderr, '\nError: no modules successfully loaded!'
        sys.exit(1)
    return modules

def _make_docmap(modules, options):
    """
    Construct the documentation map for the given modules.

    @param modules: The modules that should be documented.
    @type modules: C{list} of C{Module}
    @param options: Options from the command-line arguments.
    @type options: C{dict}
    """
    from epydoc.objdoc import DocMap, report_param_mismatches

    verbosity = options['verbosity']
    document_bases = 1
    document_autogen_vars = 1
    inheritance_groups = (options['inheritance'] == 'grouped')
    inherit_groups = (options['inheritance'] != 'grouped')
    d = DocMap(verbosity, document_bases, document_autogen_vars,
               inheritance_groups, inherit_groups)
    if options['verbosity'] > 0:
        print  >>sys.stderr, ('Building API documentation for %d modules.'
                              % len(modules))
    progress = _Progress('Building docs for', verbosity, len(modules))

    for module in modules:
        progress.report(module.__name__)
        # Add the module.  Catch any exceptions that get generated.
        try: d.add(module)
        except Exception, e:
            if options['debug']: raise
            else: _internal_error(e)
        except:
            if options['debug']: raise
            else: _internal_error()

    if not options['ignore_param_mismatch']:
        if not report_param_mismatches(d):
            estr = '    (To supress these warnings, '
            estr += 'use --ignore-param-mismatch)'
            print >>sys.stderr, estr

    return d


HEADER="""<?xml version="1.0" encoding="utf-8" ?>
<XMI xmi.version="1.1" xmlns:UML="org.omg/standards/UML">
  <XMI.header>
    <XMI.metamodel name="UML" version="1.3" href="UML.xml"/>
    <XMI.model name="PyXMPP" href="pyxmpp.xml"/>
  </XMI.header>
  <XMI.content>
    <UML:Model>
      <UML:Stereotype visibility="public" xmi.id="/Stereotype:classmethod" name="classmethod" />
      <UML:Stereotype visibility="public" xmi.id="/Stereotype:staticmethod" name="staticmethod" />
"""
FOOTER="""
    </UML:Model>
  </XMI.content>
</XMI>"""

class Formatter:
    def __init__(self,docmap):
        self.docmap=docmap

    def format(self,modules=None):
        self.generalizations=[]
        ret=HEADER
        if modules:
            from epydoc.uid import findUID
            for m in modules:
                uid=findUID(m)
                if uid.is_module():
                    print >>sys.stderr,"Formatting: %s\n" % (uid,)
                    ret+=self.format_module(uid,True)
                else:
                    print >>sys.stderr,"Skipping: %s (not a module)\n" % (uid,)
        else:
            decorated = [(u.name().lower(), u) for u in self.docmap.keys() if u.is_module()]
            decorated.sort()
            uids = [d[-1] for d in decorated]
            for uid in uids:
                if uid.is_module():
                    ret+=self.format_module(uid,False)
        ret+="\n".join(self.generalizations)+"\n"
        ret+=FOOTER
        return ret

    def format_module(self,uid,recursive):
        if recursive:
            name=uid.shortname()
        else:
            name=uid.name()
        ret="      <UML:Package xmi.id='%s' name='%s'>\n" % (escape(uid),escape(name))
        doc=self.docmap[uid]
        classes=doc.classes()
        for cls in classes:
            ret+=self.format_class(cls)
        if recursive and uid.is_package():
            modules=doc.modules()
            for mod in modules:
                ret+=self.format_module(mod.target(),True)
        ret+="      </UML:Package>\n"
        return ret

    def format_class(self,link):
        name=link.name()
        uid=link.target()
        doc=self.docmap[uid]
        descr=doc.descr()
        ret=("        <UML:Class xmi.id='%s' name='%s' comment='%s'>\n"
                % (escape(uid),escape(name),escape(descr.to_plaintext(None))))
        for meth in doc.allmethods():
            ret+=self.format_method(meth,doc)
        for att in doc.ivariables():
            ret+=self.format_attribute(att,doc)
        ret+="        </UML:Class>\n"
        for base in doc.bases():
            buid=base.target()
            g=("      <UML:Generalization xmi.id='%s(%s)'"
                    " child='%s' parent='%s' visibility='public'/>"
                    % (escape(uid),escape(buid),escape(uid),escape(buid)))
            self.generalizations.append(g)
        return ret

    def format_attribute(self,var,container):
        uid=var.uid()
        name=var.name()
        descr=var.descr()
        cuid = container.uid()
        inherited = (cuid.is_class() and uid.cls() != cuid)
        if inherited:
            return ""
        if descr:
            descr=" comment='%s'" % (escape(descr.to_plaintext(None)),)
        else:
            descr=""
        if uid.is_public():
            vis=" visibility='public'"
        else:
            vis=" visibility='private'"
        return ("          <UML:Attribute xmi.id='%s' name='%s' %s%s />\n" %
                (escape(uid),escape(name),vis,descr))

    def format_method(self,link,container):
        uid=link.target()
        name=link.name()
        doc=self.docmap[uid]
        descr=doc.descr()
        cuid = container.uid()
        inherited = (cuid.is_class() and uid.cls() != cuid)
        if inherited:
            return ""
        if name.startswith("__") and not descr:
            # ignore special/private methods without description
            return ""
        if doc is not None and uid.is_any_method() and not doc.has_docstring():
            doc = self.docmap.documented_ancestor(uid) or doc
        if descr:
            descr=" comment='%s'" % (escape(descr.to_plaintext(None)),)
        else:
            descr=""
        if uid.is_public():
            vis=" visibility='public'"
        else:
            vis=" visibility='private'"
        if uid.is_classmethod():
            st=" stereotype='/Stereotype:classmethod'"
        elif uid.is_staticmethod():
            st=" stereotype='/Stereotype:staticmethod'"
        else:
            st=""
        return ("          <UML:Operation xmi.id='%s' name='%s' %s%s%s />\n" %
                (escape(uid),escape(name),vis,descr,st))

main(sys.argv[1:])
# vi: sts=4 et sw=4
