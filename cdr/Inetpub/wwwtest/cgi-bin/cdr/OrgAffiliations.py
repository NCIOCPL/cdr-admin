#----------------------------------------------------------------------
# $Id: OrgAffiliations.py,v 1.1 2004-11-03 20:59:26 venglisc Exp $
#
# Creates a report listing Organizations and Protocol Acronym IDs
# sorted by either the Org or the Acronym.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi, cgi, time, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
orgAffil  = fields and fields.getvalue('OrgAffil') or None
SUBMENU   = "Report Menu"
buttons   = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = "OrgAffiliations.py"
title     = "CDR Administration"
section   = "Organization Affiliations Report"
now       = time.localtime(time.time())

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
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not orgAffil:
    header = cdrcgi.header(title, title, section, script, buttons)
    form   = """\
    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
    <H3>Organization Affiliations Report</H3>
    <TABLE border='0'>
     <TR>
      <TD>&nbsp;&nbsp;&nbsp;&nbsp;</TD>
      <TD><INPUT TYPE='radio' NAME='OrgAffil' VALUE='AACI' CHECKED></TD>
      <TD>
       <B>Association of American Cancer Institutes (AACI)</B>
      </TD>
     </TR>
     <TR>
      <TD>&nbsp;&nbsp;&nbsp;&nbsp;</TD>
      <TD><INPUT TYPE='radio' NAME='OrgAffil' VALUE='ACCC'></TD>
      <TD>
       <B>Association of Community Cancer Centers (ACCC)</B>
      </TD>
     </TR>
     <TR>
      <TD>&nbsp;&nbsp;&nbsp;&nbsp;</TD>
      <TD><INPUT TYPE='radio' NAME='OrgAffil' VALUE='ACS'></TD>
      <TD>
       <B>American College of Surgeons Commission on Cancer (ACS)</B>
      </TD>
     </TR>
    </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# We have a request; do what needs to be done.
#----------------------------------------------------------------------
if orgAffil:
   orgBase       = '/Organization/OrganizationLocations'
   locBase       = '/OrganizationLocation/Location'
   contactPath   = orgBase + '/CIPSContact'
   stateIdPath   = orgBase + locBase + '/PostalAddress/PoliticalSubUnit_State/@cdr:ref'
   locIdPath     = orgBase + locBase + '/@cdr:id'
   cityPath      = orgBase + locBase + '/PostalAddress/City'
   statePath     = orgBase + locBase + '/PostalAddress/PoliticalSubUnit_State'
   stateNamePath = '/PoliticalSubUnit/PoliticalSubUnitFullName'
   inclDirPath   = '/Organization/OrganizationDetails' \
                   + '/OrganizationAdministrativeInformation/IncludeInDirectory'
   affiliation   = { 'AACI':'Association of American Cancer Institutes', 
                     'ACCC':'Association of Community Cancer Centers', 
                     'ACS':'American College of Surgeons Commission on Cancer'}
      
   html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Organization Affiliations Report (%s) - %s</title>
  <basefont face='Arial, Helvetica, sans-serif'>
 </head>
 <body>
   <CENTER>
      <H2>Organization Affiliations Report (%s)</BR>
          Date: %s</H2>
   </CENTER>
  <p/>
""" % (orgAffil, time.strftime("%Y-%m-%d", now), 
       orgAffil, time.strftime("%Y-%m-%d", now))

   #----------------------------------------------------------------------
   # Create the list of Organizations with affiliations and extract the 
   # City and denormalized state.
   # Address information of City, State extracted from organization
   # location matching the CIPSContact fragment ID.
   #----------------------------------------------------------------------
   try:
      query = """\
  SELECT distinct d.id, d.title, city.value, stateName.value, 
         CASE WHEN inclDir.value = 'Include'        THEN 'Yes'
	      WHEN inclDir.value = 'Do not include' THEN 'No'
	                                            ELSE inclDir.value
	 END
    FROM document d
    JOIN query_term a
      ON d.id = a.doc_id
    JOIN query_term cc
      ON d.id = cc.doc_id
    JOIN query_term loc
      ON d.id = loc.doc_id
     AND cc.value = loc.value
    JOIN query_term city
      ON d.id = city.doc_id
     AND substring(loc.node_loc, 1, 12) = substring(city.node_loc, 1,12)
    JOIN query_term state
      ON d.id = state.doc_id
     AND substring(loc.node_loc, 1, 12) = substring(state.node_loc, 1,12)
    JOIN query_term stateId
      ON d.id = stateId.doc_id
     AND substring(loc.node_loc, 1, 12) = substring(stateId.node_loc, 1,12)
    JOIN query_term stateName
      ON stateId.int_val = stateName.doc_id
    JOIN query_term inclDir
      ON d.id = inclDir.doc_id
   WHERE a.value        = '%s'
     AND stateName.path = '%s'
     AND stateId.path   = '%s'
     AND cc.path        = '%s'
     AND loc.path       = '%s'
     AND city.path      = '%s'
     AND state.path     = '%s'
     AND inclDir.path   = '%s'
   ORDER BY stateName.value, d.title""" % (affiliation[orgAffil],
				       stateNamePath,
                                       stateIdPath, 
                                       contactPath, 
				       locIdPath, 
				       cityPath, 
				       statePath,
				       inclDirPath)
      cursor.execute(query)
      rows = cursor.fetchall()
      if not rows:
          cdrcgi.bail("Query returned no values")
   except cdrdb.Error, info:
      cdrcgi.bail('Failure fetching organizations: %s' % info[1][0])

   #----------------------------------------------------------------------
   # Put together the body of the report.
   #----------------------------------------------------------------------
   html += """\
  <table border='1' width='100%' cellspacing='0' cellpadding='5'>
   <tr>
    <td align='center' valign='bottom'>
     <b>CDR ID </b>
    </td>
    <td align='center' valign='bottom'>
     <b>Organization Title</b>
    </td>
    <td align='center' valign='bottom'>
     <b>City</b>
    </td>
    <td align='center' valign='bottom'>
     <b>State</b>
    </td>
    <td align='center' valign='bottom'>
     <b>Include in Directory</b>
    </td>
   </tr>
"""

   # ---------------------------------------------------------------------
   # Put the output in rows in a table
   # ---------------------------------------------------------------------
   for row in rows:
      html += """\
   <tr>
    <td align = 'right' valign='top'>%s</td>
    <td>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (row[0], row[1], row[2], row[3], row[4])

   html += """\
  </table>
 </body>
</html>
"""
   cdrcgi.sendPage(cdrcgi.unicodeToLatin1(html))
