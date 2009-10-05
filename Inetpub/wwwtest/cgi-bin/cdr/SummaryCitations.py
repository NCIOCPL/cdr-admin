#----------------------------------------------------------------------
#
# $Id: SummaryCitations.py,v 1.5 2009-10-02 18:29:10 venglisc Exp $
#
# Report listing all references cited in a selected version of a
# cancer information summary.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2009/07/31 19:18:49  venglisc
# Modified sort order to use the locale setting so that non-ASCII characters
# are sorted within the ASCII sequence. (Bug 4598)
#
# Revision 1.3  2009/06/24 17:36:40  venglisc
# Changing sort order by converting first to lower case. (Bug 4598)
#
# Revision 1.2  2003/10/08 18:09:09  bkline
# Changed element name from Reference to Citation to match change in
# denormalization filter.
#
# Revision 1.1  2003/05/08 20:26:42  bkline
# New summary reports.
#
#----------------------------------------------------------------------
# BZIssue::4651 - Adding PMID to citations

import xml.dom.minidom, cgi, socket, struct, re, cdr, cdrcgi, cdrdb
import locale, time

locale.setlocale(locale.LC_COLLATE, "")

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = fields and cdrcgi.getSession(fields)     or None
request    = fields and cdrcgi.getRequest(fields)     or None
docId      = fields and fields.getvalue("DocId")      or None
docTitle   = fields and fields.getvalue("DocTitle")   or None
docVersion = fields and fields.getvalue("DocVersion") or None
script     = "SummaryCitations.py"
SUBMENU    = "Report Menu"
buttons    = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
title      = "CDR Administration"
section    = "Summary Citations Report"
header     = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Display the report if we have a document ID and version number.
#----------------------------------------------------------------------
def report(docId, docVersion):
    if docVersion == "-1":
        docVersion = None
    filterSet = ['set:Denormalization Summary Set']
    response = cdr.filterDoc('guest', filterSet, docId, docVer = docVersion)
    if type(response) in (type(""), type(u"")):
        cdrcgi.bail(response)
    try:
        dom = xml.dom.minidom.parseString(response[0])
    except:
        cdrcgi.bail("Failure parsing filtered document")
    refs = []
    summaryTitle = ""
    for refList in dom.getElementsByTagName("ReferenceList"):
        for ref in refList.childNodes:
            refPmid = ""
            if ref.nodeName == "Citation":
                refString = cdr.getTextContent(ref).strip()

                if u'PMID' in ref.attributes.keys():
                    refPmid = str(ref.attributes["PMID"].value)
                if refString:
                    if refString[-1] != ".":
                        refString += "."
                    refs.append('%s [@@%s@@]' % (refString, refPmid))
    for child in dom.documentElement.childNodes:
        if child.nodeName == "SummaryTitle":
            summaryTitle = cdr.getTextContent(child)
            break
    #refs.sort(cmp=lambda x,y: cmp(x.lower(), y.lower()))
    refs.sort(lambda x, y: locale.strcoll(x.lower(), y.lower()))
    prevRef = None
    digits = re.sub(r"[^\d]", "", docId)
    id = int(digits)
    pubMedLink = ' [<a href="http://www.ncbi.nlm.nih.gov/pubmed/'
    html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>CDR%010d %s -- %s</title>
  <style type='text/css'>
   h1 { text-align: left; font-size: 18pt; font-weight: bold; }
   h2 { text-align: left; font-size: 14pt; font-weight: bold; }
   body { font-size: 12pt; font-family: Arial,sans-serif; }
  </style>
 </head>
 <body>
  <h1>%s</h1>
  <h2>References:</h2>
  <ol>
""" % (id, summaryTitle, time.strftime("%B %d, %Y"), summaryTitle)
    for ref in refs:
        if ref != prevRef:
            # Building the link for the PubMedID (format is [@@12345@@])
            # ----------------------------------------------------------
            nn = ref.find(' [@@')
            newRef = ref[:nn]    # slice off the PMID
            newId  = ref[nn+1:]  # slice off the PMID
            if newId.replace('@@', '') == '[]':
                newId = ''
            else:
                pmid  = newId[3:-3]
                newId = newId.replace('@@]', '?dopt=Abstract">' 
                                   + pmid + '</a>]').replace('[@@', pubMedLink)

            html += """\
   <li>%s%s</li>
""" % (cgi.escape(newRef), newId)
            prevRef = newRef
    cdrcgi.sendPage(html + """\
  </ol>
 </body>
</html>
""")

#----------------------------------------------------------------------
# Put up a selection list from which the user can select a version.
#----------------------------------------------------------------------
def pickVersion(docId):
    try:
        digits = re.sub(r"[^\d]", "", docId)
        id = int(digits)
    except:
        cdrcgi.bail("Invalid value for document ID: %s" % docId)
    if not id:
        cdrcgi.bail("Invalid value for document ID: %s" % docId)
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT v.num, v.dt, u.name, v.val_status, v.publishable, v.comment
              FROM doc_version v
              JOIN usr u
                ON u.id = v.usr
             WHERE v.id = ?
          ORDER BY v.num DESC""", id)
        rows = cursor.fetchall()
    except:
        raise
        cdrcgi.bail("Database failure getting document versions for %s" %
                    docId)
    if not rows:
        report(docId, None)
    elif len(rows) == 1:
        report(docId, rows[0][0])
    form = """\
   <input type='hidden' name='%s' value='%s'>
   <input type='hidden' name='DocId' value='%s'>
   Select document version:&nbsp;
   <select name='DocVersion'>
    <option value='-1' selected='1'>Current Working Version</option>
""" % (cdrcgi.SESSION, session, docId)
    for row in rows:
        # We don't use all of this information any more (at Lakshmi's request).
        ver, dt, usr, valStat, publishable, comment = row
        form += """\
    <option value='%d'>[V%d %s] %s</option>
""" % (ver, ver, dt and dt[:10] or "*** NO DATE ***",
       comment and cgi.escape(comment) or "[No comment]")
    form += """
   </select>
  </form>
 </body>
</html>
"""
    cdrcgi.sendPage(header + form)
        
#----------------------------------------------------------------------
# Use a title fragment submitted by the user to determine a doc ID.
#----------------------------------------------------------------------
def getDocId(docTitle):
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT d.id, d.title
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE d.title LIKE ?
               AND t.name = 'Summary'
          ORDER BY d.id""", docTitle + '%')
        rows = cursor.fetchall()
    except:
        cdrcgi.bail("Database failure getting document id(s) for %s" %
                    docTitle)
    if not rows:
        cdrcgi.bail("No documents found matching %s" % cgi.escape(docTitle))
    elif len(rows) == 1:
        pickVersion("CDR%010d" % rows[0][0])
    form = """\
   <input type='hidden' name='%s' value='%s'>
   <h3>More than one matching document found; please choose one.</h3>
""" % (cdrcgi.SESSION, session)
    for row in rows:
        form += """
   <input type='radio' name='DocId' value='CDR%010d'>[CDR%010d] %s<br>
""" % (row[0], row[0], cgi.escape(row[1]))
    form += """
  </form>
 </body>
</html>
"""
    cdrcgi.sendPage(header + form)
        
#----------------------------------------------------------------------
# Put up the main form for the report.
#----------------------------------------------------------------------
def getSummary():
  cdrcgi.sendPage(header + """\
   <input type='hidden' name='%s' value='%s'>
   <table>
    <tr>
     <td align='right'>Document title:&nbsp;</td>
     <td><input size='60' name='DocTitle'></td>
    </tr>
    <tr>
     <td ALIGN='right'>Document ID:&nbsp;</td>
     <td><input SIZE='60' NAME='DocId'></td>
    </tr>
   </table>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session))
    
#----------------------------------------------------------------------
# What we do depends on how much information we have.
#----------------------------------------------------------------------
if docId:
    if docVersion:
        report(docId, docVersion)
    else:
        pickVersion(docId)
elif docTitle:
    getDocId(docTitle)
else:
    getSummary()
