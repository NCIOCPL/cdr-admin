#----------------------------------------------------------------------
#
# $Id: Filter.py,v 1.7 2002-08-15 19:20:56 bkline Exp $
#
# Transform a CDR document using an XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
# Revision 1.6  2002/07/25 20:38:00  bkline
# Removed debugging code.
#
# Revision 1.5  2002/07/25 01:51:27  bkline
# Added option for DTD validation.
#
# Revision 1.4  2002/07/15 20:18:03  bkline
# Added textType argument to cdrcgi.sendPage() call.
#
# Revision 1.3  2002/01/23 18:50:22  mruben
# allow up to 8 filters
#
# Revision 1.2  2001/04/08 22:56:03  bkline
# Added Unicode mapping; switched around arguments to filterDoc call.
#
# Revision 1.1  2001/03/27 21:19:09  bkline
# Initial revision
#
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrpub, re, string

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Formatting"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Request Found", title)
session = 'guest'
docId   = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document", title)
filtId0 = fields.getvalue(cdrcgi.FILTER) or cdrcgi.bail("No Filter", title)
valFlag = fields.getvalue('validate') or 0
filtId  = [filtId0,
           fields.getvalue(cdrcgi.FILTER + "1", ""),
           fields.getvalue(cdrcgi.FILTER + "2", ""),
           fields.getvalue(cdrcgi.FILTER + "3", ""),
           fields.getvalue(cdrcgi.FILTER + "4", ""),
           fields.getvalue(cdrcgi.FILTER + "5", ""),
           fields.getvalue(cdrcgi.FILTER + "6", ""),
           fields.getvalue(cdrcgi.FILTER + "7", "")]

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
doc = cdr.filterDoc(session, filtId, docId = docId)
if type(doc) == type(()):
  doc = doc[0]

#----------------------------------------------------------------------
# Add a table row for an error or warning.
#----------------------------------------------------------------------
def addRow(type, line):
    line = line.split(":", 3)
    html = """\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top' align='right'>%s</td>
    <td valign='top' align='right'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (type, line[0], line[1], line[2], line[3])
    return html

#----------------------------------------------------------------------
# Validate the document if requested.
#----------------------------------------------------------------------
if valFlag:
    digits = re.sub('[^\d]', '', docId)
    idNum  = string.atoi(digits)
    errObj = cdrpub.validateDoc(doc, idNum)
    html = """\
<html>
 <head>
  <title>Validation results for CDR%010d</title>
 </head>
 <body>
 <h2>Validation results for CDR%010d</h2>
""" % (idNum, idNum)
    if not errObj.Warnings and not errObj.Errors:
        html += """\
 <h3>Document comes out clean: no errors, no warnings!</h3>
"""
    else:
        html += """\
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>Type</th>
    <th>Document</th>
    <th>Line</th>
    <th>Position</th>
    <th>Message</th>
   </tr>
"""
        for warning in errObj.Warnings:
            html += addRow('Warning', warning)
        for error in errObj.Errors:
            html += addRow('Error', error)
    cdrcgi.sendPage(cdrcgi.unicodeToLatin1(html + """\
 </body>
</html>
"""))

doc = cdrcgi.decode(doc)
doc = re.sub("@@DOCID@@", docId, doc)

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
textType = 'html'
if doc.find("<?xml") != -1:
    textType = 'xml'
cdrcgi.sendPage(doc, textType)
