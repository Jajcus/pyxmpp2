#!/usr/bin/python

import libxml2
import sys


class Merger:
    def __init__(self,template_file,content_file):
        self.template_doc=libxml2.parseFile(template_file)
        self.content_doc=libxml2.parseFile(content_file)
    def merge(self):
        output_doc=self.template_doc.copyDoc(True)
        slot=output_doc.xpathEval('//*[@id="main"]')[0]
        content=self.content_doc.xpathEval('//*[@class="document"]/*')
        for node in content:
            nn=slot.addChild(node.copyNode(True))
        output_doc.getRootElement().reconciliateNs(output_doc)
        return output_doc

m=Merger(sys.argv[1],sys.argv[2])
out=m.merge()
print out.serialize(format=True)
# vi: sts=4 et sw=4
