#!/usr/bin/python

import libxml2
import sys


class Merger:
    def __init__(self,model_file,auto_file):
        self.model_doc=libxml2.parseFile(model_file)
        self.auto_doc=libxml2.parseFile(auto_file)
        self.xmi_id_map={}
        self.auto_xmi_id_map={}
        self.old_elements={}
    def merge(self):
        self.output_doc=libxml2.newDoc("1.0")
        new_root=self.output_doc.newChild(None,"XMI",None)
        uml_ns=new_root.newNs("org.omg/standards/UML","UML")
        root=self.model_doc.getRootElement()
        n=root.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            if n.name=="XMI.content":
                new_content=new_root.addChild(n.docCopyNode(self.output_doc,False))
                p=n.get_properties()
                while p:
                    new_content.setProp(p.name,p.getContent())
                    p=p.next
                self.merge_xmi_content(new_content,n)
            else:
                new_root.addChild(n.docCopyNode(self.output_doc,True))
            n=n.next
        return self.output_doc
        
    def merge_xmi_content(self,target,old_content):
        self.old_elements={}
        n=old_content.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            try:
                if n.ns().getContent()=="org.omg/standards/UML" and n.name=="Model":
                    self.parse_old_model(n)
                    n=n.next
                    continue
            except libxml2.treeError:
                pass
            target.addChild(n.docCopyNode(self.output_doc,True))
            n=n.next
        auto_content=self.auto_doc.xpathEval("//XMI/XMI.content/*")
        for n in auto_content:
            if n.ns().getContent()=="org.omg/standards/UML" and n.name=="Model":
                new_model=target.addChild(n.docCopyNode(self.output_doc,False))
                p=n.get_properties()
                while p:
                    new_model.setProp(p.name,p.getContent())
                    p=p.next
                self.merge_uml_model(new_model,n)
            else:
                target.addChild(n.docCopyNode(self.output_doc,True))

    def merge_uml_model(self,target,subtree,path=""):
        n=subtree.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            
            new_node=target.addChild(n.docCopyNode(self.output_doc,False))
            p=n.get_properties()
            while p:
                old_val=p.getContent()
                if p.name in ("stereotype","parent","child"):
                    val=self.xmi_id_map.get(old_val)
                    if not val:
                        val=self.auto_xmi_id_map.get(old_val)
                    if not val:
                        val=old_val
                else:
                    val=old_val
                new_node.setProp(p.name,val)
                p=p.next
                
            npath="%s/%s:%s" % (path,n.name,n.prop("name"))
            auto_xmi_id=n.prop("xmi.id")
            xmi_id=self.xmi_id_map.get(npath)
            if xmi_id:
                if auto_xmi_id:
                    self.auto_xmi_id_map[auto_xmi_id]=xmi_id
                new_node.setProp("xmi.id",xmi_id)
            self.merge_uml_model(new_node,n,npath)
            n=n.next
        for oe in self.old_elements.get(path,[]):
            target.addChild(oe)

    def parse_old_model(self,subtree,path=""):
        n=subtree.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            if (n.ns().getContent()!="org.omg/standards/UML" or
                    n.name not in ("Stereotype","Class","Operation","Attribute","Package")):
                oe=n.docCopyNode(self.output_doc,True)
                if not path in self.old_elements:
                    self.old_elements[path]=[oe]
                else:
                    self.old_elements[path].append(oe)
                n=n.next
                continue
            npath="%s/%s:%s" % (path,n.name,n.prop("name"))
            xmi_id=n.prop("xmi.id")
            if xmi_id:
                self.xmi_id_map[npath]=xmi_id
            self.parse_old_model(n,npath)
            n=n.next

m=Merger(sys.argv[1],sys.argv[2])
out=m.merge()
print out.serialize(format=True)
