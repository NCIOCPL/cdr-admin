#----------------------------------------------------------------------
#
# $Id: EditFilter.py,v 1.4 2001-07-06 16:02:40 bkline Exp $
#
# Prototype for editing CDR filter documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2001/06/13 20:15:39  bkline
# Added code to strip carriage returns from text for TEXTAREA control.
#
# Revision 1.2  2001/04/08 22:54:59  bkline
# Added Unicode mapping calls.
#
#
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# Import required modules.
#----------------------------------------------------------------------
import cgi, cdr, re, cdrcgi, sys

#----------------------------------------------------------------------
# Set some initial values.
#----------------------------------------------------------------------
banner   = "CDR Filter Editing"
title    = "Edit CDR Filter"
BLANKDOC = """\
<CdrDoc Type='Filter'>
 <CdrDocCtl>
  <DocTitle>*** PUT YOUR TITLE HERE ***</DocTitle>
 </CdrDocCtl>
 <CdrDocXml><![CDATA[<?xml version="1.0"?>
  <xsl:transform xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                 version="1.0">
   <xsl:output method="html"/>
   <xsl:template match="/">
    *** PUT YOUR TEMPLATE RULES HERE ***
   </xsl:template>
  </xsl:transform>]]>
 </CdrDocXml>
</CdrDoc>
"""

#----------------------------------------------------------------------
# Load the fields from the form.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
if not fields: cdrcgi.bail("Unable to read form fields", banner)
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
if not session: cdrcgi.bail("Unable to log into CDR Server", banner)
if not request: cdrcgi.bail("No request submitted", banner)

#----------------------------------------------------------------------
# Display the CDR document form.
#----------------------------------------------------------------------
def showForm(doc, subBanner, buttons):
    hdr = cdrcgi.header(title, banner, subBanner, "EditFilter.py", buttons)
    html = hdr + ("<CENTER><TEXTAREA NAME='Doc' ROWS='20' COLS='80'>%s"
                  "</TEXTAREA><INPUT TYPE='hidden' NAME='%s' VALUE='%s'>"
                  "</FORM></CENTER></BODY></HTML>"
                  % (doc.replace('\r', ''), cdrcgi.SESSION, session))
    cdrcgi.sendPage(html)

#----------------------------------------------------------------------
# Remove the document ID attribute so we can save the doc under a new ID.
#----------------------------------------------------------------------
def stripId(doc):
    pattern = re.compile("(.*<CdrDoc[^>]*)\sId='[^']*'(.*)", re.DOTALL)
    return pattern.sub(r'\1\2', doc)
  
#----------------------------------------------------------------------
# Load an existing document.
#----------------------------------------------------------------------
if request == "Load":
    if not fields.has_key(cdrcgi.DOCID):
        cdrcgi.bail("No document ID specified", banner)
    doc = cdrcgi.decode(cdr.getDoc(session, fields[cdrcgi.DOCID].value, 'Y'))
    if doc.find("<Errors>") >= 0:
        cdrcgi.bail(doc, banner)
    showForm(doc, "Editing existing document", ("Load", "Save", "Clone"))

#----------------------------------------------------------------------
# Create a template for a new document.
#----------------------------------------------------------------------
elif request == 'New':
    showForm(BLANKDOC, "Editing new document", ("Load", "Save"))

#--------------------------------------------------------------------
# Create a new document using the existing data.
#----------------------------------------------------------------------
elif request == 'Clone':
    if not fields.has_key("Doc"):
        cdrcgi.bail("No document to save")
    doc = stripId(fields["Doc"].value)
    docId = cdr.addDoc(session, doc=cdrcgi.encode(doc))
    if docId.find("<Errors>") >= 0:
        cdrcgi.bail(doc, banner)
    else:
        doc = cdrcgi.decode(cdr.getDoc(session, docId, 'Y'))
        if doc.find("<Errors>") >= 0:
            cdrcgi.bail(doc, banner)
        showForm(doc, "Editing existing document", ("Load", "Save", "Clone"))

#--------------------------------------------------------------------
# Save the changes to the current document.
#----------------------------------------------------------------------
elif request == 'Save':
    if not fields.has_key("Doc"):
        cdrcgi.bail("No document to save")
    doc = fields["Doc"].value
    if re.search("<CdrDoc[^>]*\sId='[^']*'", doc, re.DOTALL):
        docId = cdr.repDoc(session, doc=cdrcgi.encode(doc))
    else:
        docId = cdr.addDoc(session, doc=cdrcgi.encode(doc))
    if docId.find("<Errors>") >= 0:
        cdrcgi.bail(doc, banner)
    else:
        doc = cdrcgi.decode(cdr.getDoc(session, docId))
        if doc.find("<Errors>") >= 0:
            cdrcgi.bail(doc, banner)
        showForm(doc, "Editing existing document", ("Load", "Save", "Clone"))

#----------------------------------------------------------------------
# Tell the user we don't know how to do what he asked.
#----------------------------------------------------------------------
else: cdrcgi.bail("Request not yet implemented: " + request, banner)
