#----------------------------------------------------------------------
#
# $Id: Filter.py,v 1.8 2002-09-16 16:35:31 pzhang Exp $
#
# Transform a CDR document using an XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
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
    for filt in filterId:  
        if not filt:
            continue      
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
    return 0

# Do all real work here.
def qcFilterSets(docId, filterId = None):
    
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
            <TD><B>Action</B></TD><TD><B>Action</B></TD><TD><B><FONT 
            COLOR=BLACK>Set Detail</B></FONT></TD></TR>\n"""
    for key in filterSets.keys():
        if not dispFilterSet(key, filterSets, filterId):
            continue

        # Form new set of filters.
        base    = "/cgi-bin/cdr/Filter.py"; 
        url     = base + "?DocId=" + docId    
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
    
        filter = "<A TARGET='_new' HREF='%s'>Filtering</A>" % url
        validate = "<A TARGET='_new' HREF='%s&validate=Y'>Validating</A>" % url
        html += """<TR><TD><FONT COLOR=BLACK>%s</FONT></TD><TD>%s</TD>
                       <TD>%s</TD><TD><FONT COLOR=BLACK>%s</FONT></TD>
                       </TR>\n""" % (key, filter, validate, 
                       dispList(filterSets[key]))
    html += "</TABLE>"
    cdrcgi.sendPage(header + html + "<BODY></HTML>")

if fields.getvalue('qcFilterSets'):
    qcFilterSets(docId, filtId)
    
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
