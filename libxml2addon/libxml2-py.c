/* Generated */

#include <Python.h>
#include <libxml/xmlversion.h>
#include <libxml/tree.h>
#include "libxml_wrap.h"
#include "libxml2-py.h"
#include "proto.h"

PyObject *
libxml_xmlRemoveNs(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlNodePtr c_retval;
    xmlNodePtr tree;
    PyObject *pyobj_tree;
    xmlNsPtr ns;
    PyObject *pyobj_ns;

    if (!PyArg_ParseTuple(args, (char *)"OO:xmlRemoveNs", &pyobj_tree, &pyobj_ns))
        return(NULL);
    tree = (xmlNodePtr) PyxmlNode_Get(pyobj_tree);
    ns = (xmlNsPtr) PyxmlNode_Get(pyobj_ns);

    c_retval = xmlRemoveNs(tree, ns);
    py_retval = libxml_xmlNodePtrWrap((xmlNodePtr) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlReplaceNs(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlNsPtr c_retval;
    xmlNodePtr tree;
    PyObject *pyobj_tree;
    xmlNsPtr oldNs;
    PyObject *pyobj_oldNs;
    xmlNsPtr newNs;
    PyObject *pyobj_newNs;

    if (!PyArg_ParseTuple(args, (char *)"OOO:xmlReplaceNs", &pyobj_tree, &pyobj_oldNs, &pyobj_newNs))
        return(NULL);
    tree = (xmlNodePtr) PyxmlNode_Get(pyobj_tree);
    oldNs = (xmlNsPtr) PyxmlNode_Get(pyobj_oldNs);
    newNs = (xmlNsPtr) PyxmlNode_Get(pyobj_newNs);

    c_retval = xmlReplaceNs(tree, oldNs, newNs);
    py_retval = libxml_xmlNsPtrWrap((xmlNsPtr) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderCurrentDoc(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlDocPtr c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderCurrentDoc", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderCurrentDoc(reader);
    py_retval = libxml_xmlDocPtrWrap((xmlDocPtr) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderExpand(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlNodePtr c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderExpand", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderExpand(reader);
    py_retval = libxml_xmlNodePtrWrap((xmlNodePtr) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderXmlLang(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderXmlLang", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderXmlLang(reader);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderMoveToFirstAttribute(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderMoveToFirstAttribute", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderMoveToFirstAttribute(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderGetAttributeNs(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;
    xmlChar * localName;
    xmlChar * namespaceURI;

    if (!PyArg_ParseTuple(args, (char *)"Ozz:xmlTextReaderGetAttributeNs", &pyobj_reader, &localName, &namespaceURI))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderGetAttributeNs(reader, localName, namespaceURI);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderGetParserProp(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;
    int prop;

    if (!PyArg_ParseTuple(args, (char *)"Oi:xmlTextReaderGetParserProp", &pyobj_reader, &prop))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderGetParserProp(reader, prop);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderIsDefault(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderIsDefault", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderIsDefault(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderHasValue(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderHasValue", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderHasValue(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderMoveToAttributeNo(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;
    int no;

    if (!PyArg_ParseTuple(args, (char *)"Oi:xmlTextReaderMoveToAttributeNo", &pyobj_reader, &no))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderMoveToAttributeNo(reader, no);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderMoveToAttributeNs(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;
    xmlChar * localName;
    xmlChar * namespaceURI;

    if (!PyArg_ParseTuple(args, (char *)"Ozz:xmlTextReaderMoveToAttributeNs", &pyobj_reader, &localName, &namespaceURI))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderMoveToAttributeNs(reader, localName, namespaceURI);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderNext(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderNext", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderNext(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderReadOuterXml(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderReadOuterXml", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderReadOuterXml(reader);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderMoveToAttribute(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;
    xmlChar * name;

    if (!PyArg_ParseTuple(args, (char *)"Oz:xmlTextReaderMoveToAttribute", &pyobj_reader, &name))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderMoveToAttribute(reader, name);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderLocatorLineNumber(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderLocatorPtr locator;
    PyObject *pyobj_locator;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderLocatorLineNumber", &pyobj_locator))
        return(NULL);
    locator = (xmlTextReaderLocatorPtr) PyxmlStreamReaderLocator_Get(pyobj_locator);

    c_retval = xmlStreamReaderLocatorLineNumber(locator);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderIsValid(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderIsValid", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderIsValid(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlNewStreamReader(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlTextReaderPtr c_retval;
    xmlParserInputBufferPtr input;
    PyObject *pyobj_input;
    char * URI;

    if (!PyArg_ParseTuple(args, (char *)"Oz:xmlNewStreamReader", &pyobj_input, &URI))
        return(NULL);
    input = (xmlParserInputBufferPtr) PyinputBuffer_Get(pyobj_input);

    c_retval = xmlNewStreamReader(input, URI);
    py_retval = libxml_xmlStreamReaderPtrWrap((xmlTextReaderPtr) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderGetAttributeNo(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;
    int no;

    if (!PyArg_ParseTuple(args, (char *)"Oi:xmlTextReaderGetAttributeNo", &pyobj_reader, &no))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderGetAttributeNo(reader, no);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderNodeType(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderNodeType", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderNodeType(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderReadAttributeValue(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderReadAttributeValue", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderReadAttributeValue(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderLookupNamespace(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;
    xmlChar * prefix;

    if (!PyArg_ParseTuple(args, (char *)"Oz:xmlTextReaderLookupNamespace", &pyobj_reader, &prefix))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderLookupNamespace(reader, prefix);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderClose(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderClose", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderClose(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}


PyObject *
libxml_xmlStreamReaderMoveToElement(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderMoveToElement", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderMoveToElement(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderLocalName(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderLocalName", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderLocalName(reader);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderRelaxNGValidate(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;
    char * rng;

    if (!PyArg_ParseTuple(args, (char *)"Oz:xmlTextReaderRelaxNGValidate", &pyobj_reader, &rng))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderRelaxNGValidate(reader, rng);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderQuoteChar(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderQuoteChar", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderQuoteChar(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderReadState(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderReadState", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderReadState(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderMoveToNextAttribute(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderMoveToNextAttribute", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderMoveToNextAttribute(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderRead(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderRead", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderRead(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderSetParserProp(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;
    int prop;
    int value;

    if (!PyArg_ParseTuple(args, (char *)"Oii:xmlTextReaderSetParserProp", &pyobj_reader, &prop, &value))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderSetParserProp(reader, prop, value);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderBaseUri(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderBaseUri", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderBaseUri(reader);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderHasAttributes(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderHasAttributes", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderHasAttributes(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderNormalization(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderNormalization", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderNormalization(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderRelaxNGSetSchema(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;
    xmlRelaxNGPtr schema;
    PyObject *pyobj_schema;

    if (!PyArg_ParseTuple(args, (char *)"OO:xmlTextReaderRelaxNGSetSchema", &pyobj_reader, &pyobj_schema))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);
    schema = (xmlRelaxNGPtr) PyrelaxNgSchema_Get(pyobj_schema);

    c_retval = xmlStreamReaderRelaxNGSetSchema(reader, schema);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlNewStreamReaderFilename(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlTextReaderPtr c_retval;
    char * URI;

    if (!PyArg_ParseTuple(args, (char *)"z:xmlNewStreamReaderFilename", &URI))
        return(NULL);

    c_retval = xmlNewStreamReaderFilename(URI);
    py_retval = libxml_xmlStreamReaderPtrWrap((xmlTextReaderPtr) c_retval);
    return(py_retval);
}


PyObject *
libxml_xmlStreamReaderValue(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderValue", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderValue(reader);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderReadInnerXml(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderReadInnerXml", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderReadInnerXml(reader);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderDepth(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderDepth", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderDepth(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderNamespaceUri(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderNamespaceUri", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderNamespaceUri(reader);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderName(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderName", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderName(reader);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderIsEmptyElement(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderIsEmptyElement", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderIsEmptyElement(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderAttributeCount(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    int c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderAttributeCount", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderAttributeCount(reader);
    py_retval = libxml_intWrap((int) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderPrefix(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderPrefix", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderPrefix(reader);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderReadString(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderReadString", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderReadString(reader);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderGetAttribute(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;
    xmlChar * name;

    if (!PyArg_ParseTuple(args, (char *)"Oz:xmlTextReaderGetAttribute", &pyobj_reader, &name))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderGetAttribute(reader, name);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderCurrentNode(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlNodePtr c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderCurrentNode", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderCurrentNode(reader);
    py_retval = libxml_xmlNodePtrWrap((xmlNodePtr) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderGetRemainder(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlParserInputBufferPtr c_retval;
    xmlTextReaderPtr reader;
    PyObject *pyobj_reader;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderGetRemainder", &pyobj_reader))
        return(NULL);
    reader = (xmlTextReaderPtr) PyxmlStreamReader_Get(pyobj_reader);

    c_retval = xmlStreamReaderGetRemainder(reader);
    py_retval = libxml_xmlParserInputBufferPtrWrap((xmlParserInputBufferPtr) c_retval);
    return(py_retval);
}

PyObject *
libxml_xmlStreamReaderLocatorBaseURI(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
    PyObject *py_retval;
    xmlChar * c_retval;
    xmlTextReaderLocatorPtr locator;
    PyObject *pyobj_locator;

    if (!PyArg_ParseTuple(args, (char *)"O:xmlTextReaderLocatorBaseURI", &pyobj_locator))
        return(NULL);
    locator = (xmlTextReaderLocatorPtr) PyxmlStreamReaderLocator_Get(pyobj_locator);

    c_retval = xmlStreamReaderLocatorBaseURI(locator);
    py_retval = libxml_xmlCharPtrWrap((xmlChar *) c_retval);
    return(py_retval);
}
