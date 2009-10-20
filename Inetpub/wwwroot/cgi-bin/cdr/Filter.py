#----------------------------------------------------------------------
#
# $Id$
#
# Transform a CDR document using an XSL/T filter and send it back to
# the browser.
#
# $Log: not supported by cvs2svn $
# Revision 1.32  2009/05/06 18:18:22  venglisc
# Converted output to unicode to match sendPage input requirements. (Bug 4560)
#
# Revision 1.31  2008/08/18 16:25:07  venglisc
# Fixed error that prevented a warning message to be displayed.
#
# Revision 1.30  2008/08/05 14:23:41  venglisc
# Modified program to allow passing of DTD file for validation. (Bug 4123)
#
# Revision 1.29  2008/04/22 17:57:44  venglisc
# Modified script to allow display of internal/external comments (Bug 2920).
#
# Revision 1.28  2008/02/26 23:32:14  venglisc
# Modifications to use Lxml as our validator instead of pyXML.
# Minor modifications to make HTML output valid.  (Bug 3923)
#
# Revision 1.27  2005/10/28 21:05:39  venglisc
# Added displayAudience variable to allow GlossaryTerm RS reports to
# be displayed with only Patient or HP term definitions. (Bug 1883)
#
# Revision 1.26  2005/07/28 21:46:14  venglisc
# Modified to allow CDRID to be entered without the prefix 'CDR'.
#
# Revision 1.25  2005/05/14 00:01:45  venglisc
# Added code to allow display of editorial and advisory board markup to
# be displayed. (Bug 1683)
#
# Revision 1.24  2004/07/13 18:39:17  ameyer
# Provide for insertion and deletion revision levels (bug #846).
# Allow for displaying of glossary terms and standard wording elements.
# [Done by Volker - checked in by Alan].
#
# Revision 1.23  2004/02/19 21:29:11  ameyer
# Allow user interface to pass a port id.
#
# Revision 1.22  2003/11/12 22:47:30  bkline
# Forced string conversion of docVer to make string concatenation work.
#
# Revision 1.21  2003/08/29 14:54:52  bkline
# Modified approach to gathering filter set information, replacing
# a hand-maintained file in the file system with filter set info
# extracted directly from the CDR database tables.
#
# revision 1.20  2003/08/28 23:01:36  venglisc
# Renamed the refLevels variable to insRevLevels.  This is needed because
# we need to pass an additional parameter for delRevLevels to handle
# bold/underline reports.
#
# Revision 1.19  2003/04/09 20:09:05  pzhang
# Added feature to handle Insertion/Deletion with RevisionLevel.
#
# Revision 1.18  2003/03/04 21:32:23  pzhang
# Fixed a bug introduced by using not-list for filter parameter
# in filterDoc().
#
# Revision 1.17  2003/03/04 19:07:57  pzhang
# Added feature to handle message instruction with terminate='no'.
#
# Revision 1.16  2002/10/21 15:42:02  pzhang
# Added port parameter into lastVersions() and filterDoc().
#
# Revision 1.15  2002/09/25 15:03:43  pzhang
# Default docVer to 0 when no value is given.
#
# Revision 1.14  2002/09/24 20:59:52  pzhang
# Added 'last' and 'lastp' for Doc Version input.
#
# Revision 1.13  2002/09/24 20:12:28  pzhang
# Added DocVersion to the page.
#
# Revision 1.12  2002/09/20 16:24:24  pzhang
# Added 8 more input boxes to allow 15 filters.
#
# Revision 1.11  2002/09/19 21:16:02  pzhang
# Sorted filterSets keys.
#
# Revision 1.10  2002/09/19 21:00:15  pzhang
# Display all filter sets when no filter is given.
#
# Revision 1.9  2002/09/16 16:58:36  pzhang
# Stripped off whitespaces in filters
#
# Revision 1.8  2002/09/16 16:35:31  pzhang
# Added "QC Filter Sets" feature.
#
# Revision 1.7  2002/08/15 19:20:56  bkline
# Eliminated hard-wired CDR login credentials.
#
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
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrpub, re, string, xml.dom.minidom

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Formatting"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Request Found", title)
session = 'guest'
cdrPort = fields.getvalue('port') or cdr.getPubPort()
cdrPort = int(cdrPort)
PDQDTD  = fields.getvalue('newdtd') or cdr.DEFAULT_DTD 
if not PDQDTD == cdr.DEFAULT_DTD:
    PDQDTD = cdr.PDQDTDPATH + '\\' + PDQDTD

docId   = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document", title)
docVer  = fields.getvalue('DocVer') or 0
docVers = cdr.lastVersions('guest', cdr.normalize(docId), port = cdrPort)

if docVer == 'last':
    docVer = '%d' % docVers[0]
elif docVer == 'lastp':
    docVer = '%d' % docVers[1]
filtId0 = fields.getvalue(cdrcgi.FILTER)
if not fields.getvalue('qcFilterSets'):
    filtId0 or cdrcgi.bail("No Filter", title)
valFlag = fields.getvalue('validate') or 0
filtId  = [filtId0,
           fields.getvalue(cdrcgi.FILTER + "1", ""),
           fields.getvalue(cdrcgi.FILTER + "2", ""),
           fields.getvalue(cdrcgi.FILTER + "3", ""),
           fields.getvalue(cdrcgi.FILTER + "4", ""),
           fields.getvalue(cdrcgi.FILTER + "5", ""),
           fields.getvalue(cdrcgi.FILTER + "6", ""),
           fields.getvalue(cdrcgi.FILTER + "7", ""),
           fields.getvalue(cdrcgi.FILTER + "8", ""),
           fields.getvalue(cdrcgi.FILTER + "9", ""),
           fields.getvalue(cdrcgi.FILTER + "10", ""),
           fields.getvalue(cdrcgi.FILTER + "11", ""),
           fields.getvalue(cdrcgi.FILTER + "12", ""),
           fields.getvalue(cdrcgi.FILTER + "13", ""),
           fields.getvalue(cdrcgi.FILTER + "14", ""),
           fields.getvalue(cdrcgi.FILTER + "15", "")]

insRevLevels = (fields.getvalue('publish')   == 'true') and 'publish_' or ''
insRevLevels += (fields.getvalue('approved') == 'true') and 'approved_' or ''
insRevLevels += (fields.getvalue('proposed') == 'true') and 'proposed_' or ''
insRevLevels += (fields.getvalue('rejected') == 'true') and 'rejected_' or ''
insRevLevels += fields.getvalue('insRevLevels') or '' # insRevLevels from links.
delRevLevels  = (fields.getvalue('rsmarkup') == 'false') and 'Y' or 'N'
displayBoard = (fields.getvalue('editorial') == 'true') and 'editorial-board_' or ''
displayBoard += (fields.getvalue('advisory') == 'true') and 'advisory-board' or ''
displayAudience = (fields.getvalue('glosspatient') == 'true') and 'patient_' or ''
displayAudience += (fields.getvalue('glosshp') == 'true') and 'hp' or ''

vendorOrQC = (fields.getvalue('QC') == 'true') and 'QC' or ''
vendorOrQC += fields.getvalue('vendorOrQC') or '' # vendorOrQC from links.
displayIComments = (fields.getvalue('internal') == 'true') and 'Y' or None
displayEComments = (fields.getvalue('external') == 'true') and 'Y' or None
displayGlossary  = (fields.getvalue('glossary') == 'true') and 'Y' or 'N'
displayStdWord   = (fields.getvalue('stdword')  == 'true') and 'Y' or 'N'
          # empty insRevLevels is expected.

# ---------------------------------------------------------------
# Passing a single parameter to the filter to decide if only the 
# internal, external, all, or none of the comments should be
# displayed.
# ---------------------------------------------------------------
if not displayIComments and not displayEComments:
    displayComments = 'N'  # No comments
elif displayIComments and not displayEComments:
    displayComments = 'I'  # Internal comments only
elif not displayIComments and displayEComments:
    displayComments = 'E'  # External comments only (default)
else:
    displayComments = 'A'  # All comments

filterParm = [['insRevLevels',            insRevLevels],
              ['delRevLevels',            delRevLevels],
              ['DisplayComments',         displayComments],
              ['DisplayGlossaryTermList', displayGlossary],
              ['ShowStandardWording',     displayStdWord],
              ['displayBoard',            displayBoard],
              ['displayAudience',         displayAudience]]
if vendorOrQC:
    filterParm.append(['vendorOrQC', 'QC'])

#----------------------------------------------------------------------
# QC Filter Sets.
#----------------------------------------------------------------------

# Display a list of filters.
def displayFilterList(set):
    strRet = ""
    for element in set.members:
        strRet += "%s:%s<BR>" % (element.id, element.name)
    return strRet

#----------------------------------------------------------------------
# Determine whether we want to show this filter set.  If any filters
# are explicitly listed in the filter data entry fields, then we
# only want to show those filters which contain *all* of the filters
# so listed.
#----------------------------------------------------------------------
def wantFilterSet(filterSet, filterIds):

    # If no filters are explicitly identified, show all the filter sets.
    if not filterIds:
        return 1

    idsInSet = [cdr.exNormalize(m.id)[1] for m in filterSet.members]
    for filterId in filterIds:
        if filterId not in idsInSet:
            return 0
    return 1

#----------------------------------------------------------------------
# Show the user the filter sets that contain the filter(s) identified.
#----------------------------------------------------------------------
def qcFilterSets(docId, docVer, filterId = None):

    #------------------------------------------------------------------
    # Get the filter sets from the server.
    #------------------------------------------------------------------
    filterSets = cdr.expandFilterSets('guest')

    #------------------------------------------------------------------
    # Create a list of the ids for the explicitly named filters.
    #------------------------------------------------------------------
    filterIds = []
    filters = cdr.getFilters('guest')
    for id in filterId:
        if id:
            if id.startswith('name:'):
                name = id[5:].upper()
                found = 0
                for filter in filters:
                    if name == filter.name.upper():
                        filterIds.append(cdr.exNormalize(filter.id)[1])
                        found = 1
                        break
                if not found:
                    cdrcgi.bail("Unknown filter: %s" % id[5:])
            elif not id.startswith('set:'): # silently ignore named sets
                try:
                    filterIds.append(cdr.exNormalize(id)[1])
                except Exception, info:
                    cdrcgi.bail("Invalid filter [%s]: %s" % (id, str(info)))

    #----------------------------------------------------------------------
    # Format HTML page.
    #----------------------------------------------------------------------
    title   = "CDR XSLT Filtering"
    section = "QC Filter Sets"
    header  = cdrcgi.header(title, title, section, "Filter.py", "")

    html = "<TABLE BORDER=1>\n"
    html += """<TR><TD><FONT COLOR=BLACK><B>Set Name</B></FONT></TD>
            <TD><CENTER><B>Action</B></CENTER></TD><TD><B><FONT
            COLOR=BLACK>Set Detail</B></FONT></TD></TR>\n"""
    keys = filterSets.keys()
    keys.sort()
    for key in keys:
        if not wantFilterSet(filterSets[key], filterIds):
            continue

        # Form new set of filters.
        revLevels = ""
        base    = "/cgi-bin/cdr/Filter.py";
        url     = base + "?DocId=" + docId + "&DocVer=" + str(docVer) + \
                  "&revLevels=" + revLevels + "&vendorOrQC=" + vendorOrQC
        i = 0
        for filt in filterSets[key].members:
            id = str(cdr.exNormalize(filt.id)[1])
            if i == 0:
                url += "&Filter=" + id
            else:
                url += "&Filter%d=" % i + id
            i += 1

        filter = "<A TARGET='_new' HREF='%s'>Filter</A>" % url
        validate = "<A TARGET='_new' HREF='%s&validate=Y'>Validate</A>" % url
        html += """<TR><TD><FONT COLOR=BLACK>%s</FONT></TD><TD>%s&nbsp;%s</TD>
                       <TD><FONT COLOR=BLACK>%s</FONT></TD>
                       </TR>\n""" % (key, filter, validate,
                       displayFilterList(filterSets[key]))
    html += "</TABLE>"
    cdrcgi.sendPage(header + html + "<BODY></HTML>")

if fields.getvalue('qcFilterSets'):
    qcFilterSets(docId, docVer, filtId)

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
filterWarning = ""
doc = cdr.filterDoc(session, filtId, docId = docId, docVer = docVer,
                    parm = filterParm, port = cdrPort)
if type(doc) == type(()):
    if doc[1]: filterWarning += doc[1]
    doc = doc[0]

#----------------------------------------------------------------------
# Add a table row for an error or warning.
#----------------------------------------------------------------------
def addRow(type, line):
    # Adding Type (Error/Warning), CDR-ID, Line#, Message
    line = line.split(":", 3)
    html = """\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (type, line[0], line[1], line[2])
    return html

#----------------------------------------------------------------------
# Validate the document if requested.
#----------------------------------------------------------------------
if valFlag:
    digits = re.sub('[^\d]', '', docId)
    idNum  = string.atoi(digits)
    errObj = cdrpub.validateDoc(doc, idNum, dtd = PDQDTD)
    html = u"""\
<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
                      'http://www.w3.org/TR/html4/loose.dtd'>
<html>
 <head>
  <title>Validation results for CDR%d</title>
  <meta http-equiv='Content-Type' content='text/html;charset=utf-8'>
  <link rel='shortcut icon' href='/favicon.ico'>
  <LINK TYPE='text/css' REL='STYLESHEET' HREF='/stylesheets/dataform.css'>
 </head>
 <body>
 <h2>Validation results for CDR%d</h2>
""" % (idNum, idNum)
    if not errObj and not filterWarning:
        html += u"""\
 <h3>Document is valid: no errors, no warnings!</h3>
"""
    else:
        html += u"""\
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>Type</th>
    <th>Document</th>
    <th>Line</th>
    <th>Message</th>
   </tr>
"""
        if filterWarning:
            html += addRow(u'Warning', u'%d:N/A:%s' % (idNum, filterWarning))
        for error in errObj:
            html += addRow(error.level_name, u'%d:%s:%s' % (idNum, 
                                                         error.line,
                                                         error.message))
        html += u" </table> "
    cdrcgi.sendPage(html + u"""\
 </body>
</html>
""")

doc = cdrcgi.decode(doc)
doc = re.sub("@@DOCID@@", docId, doc)

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
textType = 'html'
if doc.find("<?xml") != -1:
    textType = 'xml'

# Converting doc since sendPage() expexts unicode.
# ------------------------------------------------
doc = doc.decode('utf-8')
cdrcgi.sendPage(doc, textType)
