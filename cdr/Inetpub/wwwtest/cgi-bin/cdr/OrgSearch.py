#----------------------------------------------------------------------
#
# $Id: OrgSearch.py,v 1.1 2001-07-17 19:17:43 bkline Exp $
#
# Prototype for duplicate-checking interface for Organization documents.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re

#----------------------------------------------------------------------
# Named constants.
#----------------------------------------------------------------------
SCRIPT  = '/cgi-bin/cdr/Filter.py'

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
boolOp  = fields and fields.getvalue("Boolean")          or "AND"
orgName = fields and fields.getvalue("OrgNameTextfield") or None
city    = fields and fields.getvalue("CityTextfield")    or None
state   = fields and fields.getvalue("StateTextfield")   or None
country = fields and fields.getvalue("CountryTextfield") or None
zip     = fields and fields.getvalue("ZipCodeTextfield") or None
submit  = fields and fields.getvalue("SubmitButton")     or None
help    = fields and fields.getvalue("HelpButton")       or None

if help: 
    cdrcgi.bail("Sorry, help for this interface has not yet been developed.")

#----------------------------------------------------------------------
# Determine whether query contains unescaped wildcards.
#----------------------------------------------------------------------
def getQueryOp(query):
    escaped = 0
    for char in query:
        if char == '\\':
            escaped = not escaped
        elif not escaped and char in "_%": return "contains"
    return "="

#----------------------------------------------------------------------
# Escape double quotes in string.
#----------------------------------------------------------------------
quoteExpr = re.compile(r'(?<!\\)"')
def getQueryVal(val):
    return re.sub(quoteExpr, r'\"', val)

#----------------------------------------------------------------------
# Query components.
#----------------------------------------------------------------------
class SearchField:
    def __init__(self, var, path):
        self.var  = var
        self.path = path

searchFields = (SearchField(orgName, "CdrCtl/Title"),
                SearchField(city,    "CdrAttr/Org/OrgCity"),
                SearchField(state,   "CdrAttr/Org/OrgState"),
                SearchField(country, "CdrAttr/Org/OrgCountry"),
                SearchField(zip,     "CdrAttr/Org/OrgPostalCode"))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
query = ""
usesQueryTermTable = 0
boolOp = boolOp == "AND" and " and " or " or "
for searchField in searchFields:
    if searchField.var:
        queryOp  = getQueryOp(searchField.var)
        queryVal = getQueryVal(searchField.var)
        if query:
            query += boolOp
        query += '%s %s "%s"' % (searchField.path, queryOp, queryVal)
        if searchField.path.startswith('CdrAttr'): usesQueryTermTable = 1

if query and not usesQueryTermTable:
    query += ' and CdrCtl/DocType = "Org"'

#----------------------------------------------------------------------
# Submit the query to the CDR.
#----------------------------------------------------------------------
if query:
    session = cdr.login('rmk', '***REDACTED***')
    hits    = cdr.search(session, query)
else:
    hits    = []
    query   = "[No values specified]"
if type(hits) == type(""): cdrcgi.bail(hits)

#----------------------------------------------------------------------
# Emit the top of the page.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML>
 <HEAD>
  <TITLE>CDR Organization Search Results</TITLE>
  <META   HTTP-EQUIV = "Content-Type" 
             CONTENT = "text/html; charset=iso-8859-1">
  <STYLE        TYPE = "text/css">
   <!--
    .Page { font-family: Arial, Helvetica, sans-serif; color: #000066 }
   -->
  </STYLE>
 </HEAD>
 <BODY       BGCOLOR = "#CCCCFF">
  <TABLE       WIDTH = "100%%" 
              BORDER = "0" 
         CELLSPACING = "0" 
               CLASS = "Page">
   <TR       BGCOLOR = "#6699FF"> 
    <TD       NOWRAP 
              HEIGHT = "26" 
             COLSPAN = "3">
     <FONT      SIZE = "+2" 
               CLASS = "Page">CDR Advanced Search Results</FONT>
    </TD>
   </TR>
   <TR       BGCOLOR = "#FFFFCC"> 
    <TD       NOWRAP 
             COLSPAN = "3">
     <SPAN     CLASS = "Page">
      <FONT     SIZE = "+1">Organization</FONT>
     </SPAN>
    </TD>
   </TR>
   <TR> 
    <TD       NOWRAP 
             COLSPAN = "3"
              HEIGHT = "20">&nbsp;</TD>
   </TR>
   <TR> 
    <TD       NOWRAP
             COLSPAN = "3"
               CLASS = "Page">
     <FONT     COLOR = "#000000">%d documents match '%s'</FONT>
    </TD>
   </TR>
   <TR> 
    <TD       NOWRAP
             COLSPAN = "3"
               CLASS = "Page">&nbsp;</TD>
   </TR>
""" % (len(hits), query)

for i in range(len(hits)):
    docId = hits[i].docId
    title = hits[i].docTitle
    html += """\
   <TR>
    <TD       NOWRAP
               WIDTH = "10"
              VALIGN = "top">
     <DIV      ALIGN = "right">%d.</DIV>
    </TD>
    <TD        WIDTH = "20"
              VALIGN = "top">
     <A         HREF = "%s?DocId=%s&Filter=%s">%s</A>
    </TD>
    <TD        WIDTH = "74%%">%s</TD>
   </TR>
""" % (i + 1, SCRIPT, docId, 'CDR210816', docId, cgi.escape(title, 1))

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + "  </TABLE>\n </BODY>\n</HTML>\n")
