/*
 * tree.c : implementation of access function for an XML tree.
 *
 * References:
 *   XHTML 1.0 W3C REC: http://www.w3.org/TR/2002/REC-xhtml1-20020801/
 *
 * See Copyright for the status of this software.
 *
 * daniel@veillard.com
 *
 */

#define IN_LIBXML
#include "libxml.h"

#include <string.h> /* for memset() only ! */

#ifdef HAVE_CTYPE_H
#include <ctype.h>
#endif
#ifdef HAVE_STDLIB_H
#include <stdlib.h>
#endif
#ifdef HAVE_ZLIB_H
#include <zlib.h>
#endif

#include <libxml/xmlmemory.h>
#include <libxml/tree.h>
#include <libxml/parser.h>
#include <libxml/uri.h>
#include <libxml/entities.h>
#include <libxml/valid.h>
#include <libxml/xmlerror.h>
#include <libxml/parserInternals.h>
#include <libxml/globals.h>
#ifdef LIBXML_HTML_ENABLED
#include <libxml/HTMLtree.h>
#endif

/**
 * xmlRemoveNs:
 * @tree:  a node from which to remove namespace declaration
 * @ns:  a namespace to remove
 *
 * This function removes namespace declaration from a node. It will
 * refuse to do so if the namespace is used somwhere in the subtree.
 *
 * Returns the tree pointer or NULL in case of error
 */
xmlNodePtr
xmlRemoveNs(xmlNodePtr tree,xmlNsPtr ns) {
    xmlNsPtr nsDef,prev;
    xmlNodePtr node = tree;
    xmlNodePtr declNode = NULL;
    xmlAttrPtr attr;

    if (ns == NULL) {
         xmlGenericError(xmlGenericErrorContext,
                    "xmlRemoveNs : NULL namespace\n");
         return(NULL);
    }
    while (node != NULL) {
        /*
         * Check if the namespace is in use by the node
         */
        if (node->ns == ns) {
             xmlGenericError(xmlGenericErrorContext,
                    "xmlRemoveNs : namespace in use\n");
             return(NULL);
        }

        /*
         * now check for namespace hold by attributes on the node.
         */
        attr = node->properties;
        while (attr != NULL) {
            if (attr->ns == ns) {
                xmlGenericError(xmlGenericErrorContext,
                    "xmlRemoveNs : namespace in use\n");
                return(NULL);
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
            if (node == tree)
                node = NULL;
        } else
            break;
    }

    /* there is no such namespace declared here */
    if (declNode == NULL) {
        return(tree);
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

    return(tree);
}

/**
 * xmlReplaceNs:
 * @tree:  a subtree where the replacement will be done
 * @oldNs: the old namespace
 * @newNs: the new namespace
 *
 * This function replaces oldNs with newNs evereywhere within the tree.
 * oldNs declaration is left untouched. xmlReconciliateNs or xmlRemoveNs
 * should be used afterwards. Both oldNs and newNs may be NULL.
 *
 * Returns the tree pointer or NULL in case of error
 */
xmlNsPtr
xmlReplaceNs(xmlNodePtr tree,xmlNsPtr oldNs,xmlNsPtr newNs) {
    xmlNodePtr node = tree;
    xmlAttrPtr attr;

    while (node != NULL) {
        /*
         * Check if the namespace is in use by the node
         */
        if (node->ns == oldNs) {
            node->ns = newNs;
        }

        /*
         * now check for namespace hold by attributes on the node.
         */
        attr = node->properties;
        while (attr != NULL) {
            if (attr->ns == oldNs) {
                node->ns = newNs;
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
            if (node == tree)
                node = NULL;
        } else
            break;
    }

    return(tree);
}
