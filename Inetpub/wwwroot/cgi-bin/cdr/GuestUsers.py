#----------------------------------------------------------------------
#
# $Id$
#
# Main menu for Guest Users
# -------------------------
# We want to prevent that guest users might accidentally modify data
# or submit a publishing job.  Therefore, we're limiting the menu
# options to these users that are guest group members.
#
# BZIssue::4653 CTRO Access to CDR Admin Interface
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = "guest"

#----------------------------------------------------------------------
# Put up the menu.
#----------------------------------------------------------------------
session = "?%s=%s" % (cdrcgi.SESSION, session)
title   = "CDR Administration"
section = "Guest Users"
buttons = []
html    = cdrcgi.header(title, title, section, "", buttons,
                        stylesheet = """
        <style type='text/css'>
        </style>
            
        <script language='JavaScript'>
          function setCdrId() {
             var link = document.getElementById('pp2link');
             var docid = document.getElementById('cdrid').value;
             var pp2link = link + docid;
             document.getElementById('pp2link').href = pp2link
             }

          function setDocType() {
             var link = document.getElementById('pplink');
             var index = document.getElementById('ppdt').selectedIndex;
             var doctype = document.getElementById('ppdt').options[index].text;
             var pplink = link + doctype;
             document.getElementById('pplink').href = pplink
             }
        </script>
        """) + """\
   <ol>
"""
items   = (('AdvancedSearch.py',       'Advanced Search Menu'          ),
           ('PublishPreview.py',       'Publish Preview'),
           ('TerminologyReports.py',   'Terminology Reports')
           )
for item in items:
    if item[1] == 'Publish Preview2':
        if not cdr.isDevHost():
            continue
        html += """\
    <li><a href='%s/%s%s&ReportType=pp&DocType=' 
           id="pplink" onclick=setDocType()>%s</a> &nbsp;
    <select name="pptype" size="1" id="ppdt">
     <option value="1">CTGovProtocol</option>
     <option value="2">DrugInformationSummary</option>
     <option value="3">GlossaryTermName</option>
     <option value="4">InScopeProtocol</option>
     <option value="5">Summary</option>
    </select></li>
""" % (cdrcgi.BASE, item[0], session, item[1])
    elif item[1] == 'Publish Preview':
        if not cdr.isDevHost():
            continue
        html += """\
    <li><a href='%s/%s%s&ReportType=pp&DocId=' 
           id="pp2link" onclick=setCdrId()>%s</a> &nbsp;
    &nbsp;
    <span style="font-weight: normal;">(Enter CDR-ID)</span>&nbsp;
    <input name="ppid"  id="cdrid"></li>
""" % (cdrcgi.BASE, item[0], session, item[1])
    else:
        html += """\
    <li><a href='%s/%s%s'>%s</a></li>
""" % (cdrcgi.BASE, item[0], session, item[1])

cdrcgi.sendPage(html + """\
   </ol>
  </form>
 </body>
</html>
""")
