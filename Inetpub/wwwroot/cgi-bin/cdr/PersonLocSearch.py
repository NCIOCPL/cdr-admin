#----------------------------------------------------------------------
# Prototype for duplicate-checking interface for Person documents.
# BZIssue::3716 - unicode encoding cleanup
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
boolOp    = fields and fields.getvalue("Boolean")         or "AND"
surname   = fields and fields.getvalue("Surname")         or None
givenName = fields and fields.getvalue("GivenName")       or None
initials  = fields and fields.getvalue("Initials")        or None
submit    = fields and fields.getvalue("SubmitButton")    or None
help      = fields and fields.getvalue("HelpButton")      or None
pattern   = re.compile("<Data>(.*?)</Data>", re.DOTALL)

if help: 
    cdrcgi.bail("Sorry, help for this interface has not yet been developed.")

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
except cdrdb.Error, info:
    cdrcgi.bail('Failure connecting to CDR: %s' % info[1][0])

#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields = (('Surname',                 'Surname'),
              ('Given Name',              'GivenName'),
              ('Initials',                'Initials'))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                          "Person (Locations in Result Display) Search Form",
                          "PersonLocSearch.py",
                          fields,
                          buttons,
                          'Person',
                          conn)
    page += u"""\
  </FORM>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(page)

#----------------------------------------------------------------------
# Define the search fields used for the query.
#----------------------------------------------------------------------
searchFields = (cdrcgi.SearchField(surname,
                            ("/Person/PersonNameInformation/SurName",)),
                cdrcgi.SearchField(givenName,
                            ("/Person/PersonNameInformation/GivenName",)),
                cdrcgi.SearchField(initials,
                            ("/Person/PersonNameInformation/MiddleInitial",)))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, boolOp, 
                                                       "Person")
if not query:
    cdrcgi.bail('No query criteria specified')
                    
#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Person documents: %s' % info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = u"".join(cdrcgi.advancedSearchResultsPageTop("Person", len(rows), strings))
for i in range(len(rows)):
    docId = "CDR%010d" % rows[i][0]
    title = rows[i][1]
    html += u"""\
<TR>
<TD       NOWRAP
           WIDTH = "10"
          VALIGN = "top">
 <DIV      ALIGN = "right">%d.</DIV>
</TD>
<TD        WIDTH = "75%%">%s</TD>
<TD>&nbsp;</TD>
<TD        WIDTH = "20"
          VALIGN = "top">
 <A         HREF = "%s?DocId=%s&%s=%s">%s</A>
</TD>
</TR>
""" % (i + 1, cgi.escape(title, 1), cdrcgi.BASE + '/QcReport.py', 
       docId, cdrcgi.SESSION, session, docId)
    parms = (('docId', docId), ('repName', 'dummy'), ('includeHomeAddresses',
                                                      'yes'))
    response = cdr.filterDoc(session, ['name:Person Locations Picklist'],
                              docId = docId, parm = parms)
    if type(response) == type(""):
        errs = cdr.checkErr(response)
        if errs:
            cdrcgi.bail("Failure extracting addresses: %s" % errs)
        #cdrcgi.bail("addresses = <PRE>[%s]</PRE>" % addresses[0])
    else:
        addresses = pattern.findall(response[0])
        if addresses:
            html += u"""
<TR>
<TD>&nbsp;</TD>
<TD WIDTH="75%%">
<UL>
"""
            for address in addresses:
                html += u"<LI>%s</LI>" % unicode(address, "utf-8")
            html += u"""\
</UL>
</TD>
<TD COLSPAN="2">&nbsp;</TD>
</TR>
"""

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + u"""\
  </TABLE>
 </BODY>
</HTML>
""")
