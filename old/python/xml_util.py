#!/usr/bin/env python


'''
Somewhat element-centric utility functions for working with xml documents.  Works best with docs which are simple
hierarchies of elements rather than mixtures of of elements and text nodes.
I.e. simple hierarchy: <foo><bar>hi</bar><baz>yo</baz></foo>.  mixed text and element nodes: <foo>hi<bar>why?</bar>bye</foo>.
'''

import xml.dom


def getDocument(node):
    '''
    Useful if for example you have a node and need the document to create a new node to insert into the node.
    returns: Document object of a node in an xml document.  
    '''
    if node.parentNode == None:
        return node
    else:
        return getDocument(node.parentNode)

    
def getChildren(node, tagName=None):
    '''
    returns: list of all direct children of node which are element nodes of type tagName.
    '''
    children = []
    if node.hasChildNodes():
        for kid in node.childNodes:
            if kid.nodeType == xml.dom.Node.ELEMENT_NODE:
                if tagName == None or kid.tagName == tagName:
                    children.append(kid)
    return children


def getFirstChild(node, tagName=None):
    taggedChildren = getChildren(node, tagName=tagName)
    if taggedChildren:
        return taggedChildren[0]
    else:
        return None


def isEmpty(node):
    '''
    for the case when a node has no text or elements.  e.g. <br />
    '''
    return not node.hasChildNodes()


def getTextValue(node):
    '''
    node: xml dom node containing one child node which is a text node
    returns: string value of text child stripped of whitespace.
    '''
    return node.childNodes[0].data.strip()


def cloneElemTree(elem, doc=None):
    '''
    elem: element node to be (deep) cloned.
    doc: document node used to generate new nodes.
    returns: a deep copy including elem, all of element children of elem, and any text leaf nodes.
    '''
    if not doc:
        doc = getDocument(elem)

    newElem = doc.createElement(elem.tagName)

    # an element either has kids or text, not a combination, in this simplified version of xml.
    kids = getChildren(elem)
    if kids:
        for kid in kids:
            newElem.appendChild(cloneElemTree(kid, doc))
    elif not isEmpty(elem):
        newElem.appendChild(doc.createTextNode(getTextValue(elem)))

    return newElem
            


# last line python-mode semantic cache bug fix
