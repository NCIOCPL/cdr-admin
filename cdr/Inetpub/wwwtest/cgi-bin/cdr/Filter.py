#----------------------------------------------------------------------
#
# $Id: Filter.py,v 1.18 2003-03-04 21:32:23 pzhang Exp $
#
# Transform a CDR document using an XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
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
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrpub, re, string, xml.dom.minidom

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Formatting"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Request Found", title)
session = 'guest'
docId   = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document", title)
docVer  = fields.getvalue('DocVer') or 0
docVers = cdr.lastVersions('guest', docId, port = cdr.getPubPort())
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

#----------------------------------------------------------------------
# QC Filter Sets.
#----------------------------------------------------------------------

# Display a list of filters.
def dispList(list):
    strRet = ""
    for element in list:
        strRet += element + "<BR>"
    return strRet
        
# Show only the filterSet that matches the input filter(s).
def dispFilterSet(key, filterSets, filterId):
    filtExpr = re.compile("^(CDR)*(0*)(\d+)$", re.IGNORECASE)
    nFilters = 0
    for filt in filterId:  
        if not filt:
            continue   
        nFilters += 1 
        filt = filt.strip()  
        match = filtExpr.search(filt)
        if match:            
            id = match.group(3) + ":"          
            for filter in filterSets[key]:                              
                if -1 != filter.find(id):  
                    # cdrcgi.bail("id: %s in %s" % (id,filter),  title)             
                    return 1
        else:            
            for filter in filterSets[key]:                
                if -1 != filter.find(filt): 
                    # cdrcgi.bail("name: %s in %s" % (filt,filter),  title)      
                    return 1       
    if nFilters:
        return 0
    else:
        # Display all filter sets when no "filter" filter is given.
        return 1

# Do all real work here.
def qcFilterSets(docId, docVer, filterId = None):
    
    # Where the filtersets file is.
    # Don't want this page to be working on FRANCK or BACH.
    fileName = "d:/cdr/filters/FilterSets.xml"

    # Hash for filter set: name->[filters]
    filterSets = {}
    
    # Open the xml master file and build the hash.
    string = open(fileName, "r").read()
    docElem = xml.dom.minidom.parseString(string).documentElement     
    for node in docElem.childNodes:        
        if node.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
            name = ""
            for m in node.childNodes:
                if m.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
                    if m.nodeName == 'Name':
                        name = cdr.getTextContent(m) 
                        if not filterSets.has_key(name):
                            filterSets[name] = []
                    else:
                        filter = cdr.getTextContent(m) 
                        filterSets[name].append(filter)
   
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
        if not dispFilterSet(key, filterSets, filterId):
            continue

        # Form new set of filters.
        base    = "/cgi-bin/cdr/Filter.py"; 
        url     = base + "?DocId=" + docId + "&DocVer=" + docVer
        docIdExpr = re.compile("^(\d+):")
        i = 0        
        for filt in filterSets[key]:
            match = docIdExpr.search(filt)
            if match:            
                id = match.group(1)     
                if i == 0:
                    url += "&Filter=" + id   
                else:
                    url += "&Filter%d=" % i +  id
                i += 1             
    
        filter = "<A TARGET='_new' HREF='%s'>Filter</A>" % url
        validate = "<A TARGET='_new' HREF='%s&validate=Y'>Validate</A>" % url
        html += """<TR><TD><FONT COLOR=BLACK>%s</FONT></TD><TD>%s&nbsp;%s</TD>
                       <TD><FONT COLOR=BLACK>%s</FONT></TD>
                       </TR>\n""" % (key, filter, validate, 
                       dispList(filterSets[key]))
    html += "</TABLE>"
    cdrcgi.sendPage(header + html + "<BODY></HTML>")

if fields.getvalue('qcFilterSets'):
    qcFilterSets(docId, docVer, filtId)
    
#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
filterWarning = ""
doc = cdr.filterDoc(session, filtId, docId = docId, docVer = docVer,
                    port = cdr.getPubPort())                    
if type(doc) == type(()):
    if doc[1]: filterWarning += doc[1]
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
    if not errObj.Warnings and not errObj.Errors and not filterWarning: 
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
        if filterWarning:
            html += addRow('Warning', '%d.xml:0:0:%s' % (idNum, filterWarning))
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
