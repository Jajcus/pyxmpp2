#include <Python.h>
#include <libxml/parser.h>
#include <libxml/tree.h>
#include <libxml/SAX.h>
#include <libxml/xmlerror.h>

static PyObject *MyError;

/*
 * Code borrowed from libxml2 python bindings
 * Copyright (C) 1998-2002 Daniel Veillard.  All Rights Reserved.
 * (see Copyright-libxml2 for copyright details)
 */

#define PyxmlNode_Get(v) (((v) == Py_None) ? NULL : \
	(((PyxmlNode_Object *)(v))->obj))
	
typedef struct {
    PyObject_HEAD
    xmlNodePtr obj;
} PyxmlNode_Object;

PyObject * libxml_xmlDocPtrWrap(xmlDocPtr doc) {
    PyObject *ret;

#ifdef DEBUG
    printf("libxml_xmlDocPtrWrap: doc = %p\n", doc);
#endif
    if (doc == NULL) {
        Py_INCREF(Py_None);
        return (Py_None);
    }
    /* TODO: look at deallocation */
    ret =
        PyCObject_FromVoidPtrAndDesc((void *) doc, (char *) "xmlDocPtr",
                                     NULL);
    return (ret);
}

PyObject * libxml_xmlNodePtrWrap(xmlNodePtr node) {
    PyObject *ret;

#ifdef DEBUG
    printf("libxml_xmlNodePtrWrap: node = %p\n", node);
#endif
    if (node == NULL) {
        Py_INCREF(Py_None);
        return (Py_None);
    }
    ret =
        PyCObject_FromVoidPtrAndDesc((void *) node, (char *) "xmlNodePtr",
                                     NULL);
    return (ret);
}

/*
 * End of code borrowed from libxml2
 */

/* Tree manipulation functions */

static PyObject * remove_ns(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
PyObject *pyobj_tree,*pyobj_ns;
xmlNsPtr nsDef,prev;
xmlNodePtr node;
xmlNodePtr declNode = NULL;
xmlAttrPtr attr;
xmlNodePtr tree;
xmlNsPtr ns;

	if (!PyArg_ParseTuple(args, "OO", &pyobj_tree,&pyobj_ns)) return NULL;
	tree = (xmlNodePtr) PyxmlNode_Get(pyobj_tree);
	ns = (xmlNsPtr) PyxmlNode_Get(pyobj_ns);
	node = tree;
	
	if (ns == NULL) {
		PyErr_SetString(MyError,"remove_ns: NULL namespace");
		return NULL;
	}
	
	while (node != NULL) {
		/*
		 * Check if the namespace is in use by the node
		 */
		if (node->ns == ns) {
			PyErr_SetString(MyError,"remove_ns: NULL namespace");
			return NULL;
		}

		/*
		 * now check for namespace hold by attributes on the node.
		 */
		attr = node->properties;
		while (attr != NULL) {
			if (attr->ns == ns) {
				PyErr_SetString(MyError,"remove_ns: NULL namespace");
				return NULL;
			}
			attr = attr->next;
		}

		/*
		 * Check if the namespace is declared in the node
		 */
		nsDef=node->nsDef;
		while(nsDef != NULL) {
			if (nsDef == ns) {
				declNode = node;
				break;
			}
			nsDef=nsDef->next;
		}

		/*
		 * Browse the full subtree, deep first
		 */
		if (node->children != NULL) {
			/* deep first */
			node = node->children;
		} else if ((node != tree) && (node->next != NULL)) {
			/* then siblings */
			node = node->next;
		} else if (node != tree) {
			/* go up to parents->next if needed */
			while (node != tree) {
				if (node->parent != NULL)
					node = node->parent;
				if ((node != tree) && (node->next != NULL)) {
					node = node->next;
					break;
				}
				if (node->parent == NULL) {
				    node = NULL;
				    break;
				}
			}
			/* exit condition */
			if (node == tree) node = NULL;
		} else break;
	}

	/* there is no such namespace declared here */
	if (declNode == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	}

	prev=NULL;
	nsDef=declNode->nsDef;
	while(nsDef != NULL) {
		if (nsDef == ns) {
			if (prev == NULL) declNode->nsDef=nsDef->next;
			else prev->next=nsDef->next;
			xmlFreeNs(ns);
			break;
		}
		prev=nsDef;
		nsDef=nsDef->next;
	}

	Py_INCREF(Py_None);
	return Py_None;
}

static PyObject * replace_ns(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
PyObject *pyobj_tree,*pyobj_old_ns,*pyobj_new_ns;
xmlNodePtr tree,node;
xmlAttrPtr attr;
xmlNsPtr new_ns,old_ns;

	if (!PyArg_ParseTuple(args, "OOO", &pyobj_tree,&pyobj_old_ns,&pyobj_new_ns)) return NULL;
	tree = (xmlNodePtr) PyxmlNode_Get(pyobj_tree);
	old_ns = (xmlNsPtr) PyxmlNode_Get(pyobj_old_ns);
	new_ns = (xmlNsPtr) PyxmlNode_Get(pyobj_new_ns);
	node = tree;
	
	while (node != NULL) {
		/*
		 * Check if the namespace is in use by the node
		 */
		if (node->ns == old_ns) {
			node->ns = new_ns;
		}

		/*
		 * now check for namespace hold by attributes on the node.
		 */
		attr = node->properties;
		while (attr != NULL) {
			if (attr->ns == old_ns) {
				node->ns = new_ns;
			}
			attr = attr->next;
		}

		/*
		 * Browse the full subtree, deep first
		 */
		if (node->children != NULL) {
			/* deep first */
			node = node->children;
		} else if ((node != tree) && (node->next != NULL)) {
			/* then siblings */
			node = node->next;
		} else if (node != tree) {
			/* go up to parents->next if needed */
			while (node != tree) {
				if (node->parent != NULL) node = node->parent;
				if ((node != tree) && (node->next != NULL)) {
					node = node->next;
					break;
				}
				if (node->parent == NULL) {
					node = NULL;
					break;
				}
			}
			/* exit condition */
			if (node == tree) node = NULL;
		} else break;
	}
	
	Py_INCREF(Py_None);
	return Py_None;
}

/* Stream reader functions */

staticforward PyTypeObject ReaderType;

typedef struct _reader{
   	PyObject_HEAD

	xmlParserCtxtPtr	ctxt;
	xmlSAXHandler		sax;
	
	startElementSAXFunc	startElement;
	endElementSAXFunc	endElement;
	charactersSAXFunc	characters;
	cdataBlockSAXFunc	cdataBlock;
	processingInstructionSAXFunc processingInstruction;
	
	errorSAXFunc		error;
	fatalErrorSAXFunc	fatalError;

	PyObject		*handler;
	
	int			eof;
	int			exception;
}ReaderObject;

void myStartElement(void *ctx,const xmlChar *name,const xmlChar **atts){
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
ReaderObject *reader=(ReaderObject *)ctxt->_private;
PyObject *obj;
	
	reader->startElement(ctx,name,atts);
	if (ctxt->nodeNr==1){
		obj=PyObject_CallMethod(reader->handler,"_stream_start","O",
					libxml_xmlDocPtrWrap(ctxt->myDoc));
		if (obj==NULL) reader->exception=1;
		else Py_DECREF(obj);
	}
	else if (ctxt->nodeNr==2){
		obj=PyObject_CallMethod(reader->handler,"_stanza_start","OO",
					libxml_xmlDocPtrWrap(ctxt->myDoc),
					libxml_xmlNodePtrWrap(ctxt->node));
		if (obj==NULL) reader->exception=1;
		else Py_DECREF(obj);
	}
}

void myEndElement(void *ctx,const xmlChar *name){
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
ReaderObject *reader=(ReaderObject *)ctxt->_private;
PyObject *obj;
xmlNodePtr node;

	node=ctxt->node;
	reader->endElement(ctx,name);
	if (ctxt->nodeNr==0){
		reader->eof=1;
		obj=PyObject_CallMethod(reader->handler,"_stream_end","O",
					libxml_xmlDocPtrWrap(ctxt->myDoc));
		if (obj==NULL) reader->exception=1;
		else Py_DECREF(obj);
	}
	else if (ctxt->nodeNr==1 && node){
		obj=PyObject_CallMethod(reader->handler,"_stanza_end","OO",
					libxml_xmlDocPtrWrap(ctxt->myDoc),
					libxml_xmlNodePtrWrap(node));
		if (obj==NULL) reader->exception=1;
		else Py_DECREF(obj);
		xmlUnlinkNode(node);
		xmlFreeNode(node);
	}
}

void myCharacters(void *ctx,const xmlChar *ch,int len){
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
ReaderObject *reader=(ReaderObject *)ctxt->_private;

	if (ctxt->nodeNr>1){
		reader->characters(ctx,ch,len);
	}
}

void myCdataBlock(void *ctx,const xmlChar *value,int len){
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
ReaderObject *reader=(ReaderObject *)ctxt->_private;

	if (ctxt->nodeNr>1){
		reader->cdataBlock(ctx,value,len);
	}
}

void myProcessingInstruction(void *ctx,const xmlChar *target,const xmlChar *data){
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
ReaderObject *reader=(ReaderObject *)ctxt->_private;

	if (ctxt->nodeNr==0){
		reader->processingInstruction(ctx,target,data);
	}
}

static void myError(void *ctx, const char *msg, ...){
va_list vargs;
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
ReaderObject *reader=(ReaderObject *)ctxt->_private;
PyObject *str,*obj;

	va_start (vargs, msg);
	str=PyString_FromFormatV(msg,vargs);
	va_end (vargs);
	if (str==NULL) {
		reader->exception=1;
		return;
	}
	obj=PyObject_CallMethod(reader->handler,"error","O",str);
	Py_DECREF(str);
	if (obj==NULL) reader->exception=1;
	else Py_DECREF(obj);
}

static void myFatalError(void *ctx, const char *msg, ...){
va_list vargs;
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
ReaderObject *reader=(ReaderObject *)ctxt->_private;
PyObject *str,*obj;

	va_start (vargs, msg);
	str=PyString_FromFormatV(msg,vargs);
	va_end (vargs);
	if (str==NULL) {
		reader->exception=1;
		return;
	}
	obj=PyObject_CallMethod(reader->handler,"error","O",str);
	Py_DECREF(str);
	if (obj==NULL) reader->exception=1;
	else Py_DECREF(obj);
}

static PyObject * reader_new(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
ReaderObject *reader;
PyObject *handler;

	if (!PyArg_ParseTuple(args, "O", &handler)) return NULL;
	
	reader=PyObject_New(ReaderObject,&ReaderType);
	if (reader==NULL) return NULL;

	memcpy(&reader->sax,&xmlDefaultSAXHandler,sizeof(xmlSAXHandler));

	/* custom handlers */
	reader->startElement=reader->sax.startElement;
	reader->sax.startElement=myStartElement;
	reader->endElement=reader->sax.endElement;
	reader->sax.endElement=myEndElement;
	reader->error=reader->sax.error;
	reader->sax.error=myError;
	reader->fatalError=reader->sax.fatalError;
	reader->sax.fatalError=myFatalError;
	
	/* things processed only at specific levels */
	reader->characters=reader->sax.characters;
	reader->sax.characters=myCharacters;
	reader->cdataBlock=reader->sax.cdataBlock;
	reader->sax.cdataBlock=myCdataBlock;
	reader->processingInstruction=reader->sax.processingInstruction;
	reader->sax.processingInstruction=myProcessingInstruction;

	/* unused in XMPP */
	reader->sax.resolveEntity=NULL;
	reader->sax.getEntity=NULL;
	reader->sax.entityDecl=NULL;
	reader->sax.notationDecl=NULL;
	reader->sax.attributeDecl=NULL;
	reader->sax.elementDecl=NULL;
	reader->sax.unparsedEntityDecl=NULL;
	reader->sax.comment=NULL;
	reader->sax.externalSubset=NULL;
	
	reader->eof=0;
	reader->exception=0;
	reader->handler=handler;
	Py_INCREF(handler);
	
	reader->ctxt=xmlCreatePushParserCtxt(&reader->sax,NULL,"",0,"test.xml");
	reader->ctxt->_private=reader;
	
	return (PyObject *)reader;
}

static void reader_free(PyObject *self) {
ReaderObject *reader=(ReaderObject *)self;

	xmlFreeParserCtxt(reader->ctxt);
	Py_DECREF(reader->handler);
	PyObject_Del(self);
}

static PyObject * reader_feed(PyObject *self, PyObject *args) {
ReaderObject *reader=(ReaderObject *)self;
char *str;
int len;
int ret;

	if (!PyArg_ParseTuple(args, "s#", &str, &len)) return NULL;

	reader->exception=0;

	ret=xmlParseChunk(reader->ctxt,str,len,len==0);

	if (reader->exception) return NULL;
	
	if (ret==0){	
		Py_INCREF(Py_None);
		return Py_None;
	}

	PyErr_Format(MyError,"Parser error #%d.",ret);
	return NULL;
}

static PyObject * reader_doc(PyObject *self, PyObject *args) {
	Py_INCREF(Py_None);
	return Py_None;
}

static PyMethodDef reader_methods[] = {
	{(char *)"feed", reader_feed, METH_VARARGS, NULL},
	{(char *)"doc", reader_doc, METH_VARARGS, NULL},
	{NULL, NULL, 0, NULL}
};

static PyObject * reader_getattr(PyObject *obj, char *name) {
ReaderObject *reader=(ReaderObject *)obj;

	return Py_FindMethod(reader_methods, (PyObject *)reader, name);
}
 
static int reader_setattr(PyObject *obj, char *name, PyObject *v) {
	(void)PyErr_Format(PyExc_RuntimeError, "Read-only attribute: \%s", name);
	return -1;
}

static PyTypeObject ReaderType = {
	PyObject_HEAD_INIT(NULL)
	0,
	"_Reader",
	sizeof(ReaderObject),
	0,
	reader_free, /*tp_dealloc*/
	0,          /*tp_print*/
	reader_getattr, /*tp_getattr*/
	reader_setattr, /*tp_setattr*/
	0,          /*tp_compare*/
	0,          /*tp_repr*/
	0,          /*tp_as_number*/
	0,          /*tp_as_sequence*/
	0,          /*tp_as_mapping*/
	0,          /*tp_hash */
};

static PyMethodDef libxmlMethods[] = {
	{(char *)"replace_ns", replace_ns, METH_VARARGS, NULL },
	{(char *)"remove_ns", remove_ns, METH_VARARGS, NULL },
	{(char *)"reader_new", reader_new, METH_VARARGS, NULL},
	{NULL, NULL, 0, NULL}
};

void init_xmlextra(void) {
static int initialized = 0;
PyObject *m, *d;

	if (initialized != 0) return;
	ReaderType.ob_type = &PyType_Type;
	m = Py_InitModule((char *) "_xmlextra", libxmlMethods);
	d = PyModule_GetDict(m);
	MyError = PyErr_NewException("_xmlextra.error", NULL, NULL);
	PyDict_SetItemString(d, "error", MyError);
	initialized = 1;
}
