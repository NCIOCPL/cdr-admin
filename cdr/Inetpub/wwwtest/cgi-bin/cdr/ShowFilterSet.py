#----------------------------------------------------------------------
#
# $Id: ShowFilterSet.py,v 1.1 2003-11-10 18:12:35 bkline Exp $
#
# Drills down into a filter set recursively to show which filters
# will be applied to a document when the set is invoked.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrcgi, cgi

fields  = cgi.FieldStorage()
setName = fields and fields.getvalue('name') or None

def showMembers(members):
    if not members: return ""
    html = """\
     <ul>
"""
    for member in members:
        html += """\
      <li>
"""
        if type(member.id) == type(9):
            set = cdr.getFilterSet('guest', member.name)
            html += """\
       %s<br>
       %s
""" % (set.name, showMembers(set.members))
        else:
            html += """\
       %s: %s
""" % (member.id, member.name)
        html += """\
      </li>
"""
    html += """\
     </ul>"""
    return html

def makeFilterSetList():
    sets = cdr.getFilterSets('guest')
    if not sets:
        cdrcgi.bail("Can't find filter sets!")
    selected = " selected='1'"
    html = """\
     <select name='name'>
"""
    for set in sets:
        html += """\
      <option%s>%s</option>
""" % (selected, set.name)
        selected = ""
    return html + """\
     </select>
"""

if not setName:
    cdrcgi.sendPage("""\
<html>
 <head>
  <title>Show CDR Filter Set</title>
 </head>
 <body>
  <form>
  <b>Choose filter set:&nbsp;</b>
  %s
  &nbsp;
  <input type='submit'>
 </body>
</html>""" % makeFilterSetList())

set = cdr.getFilterSet('guest', setName)
html = """\
<html>
 <head>
  <title>Show CDR Filter Set</title>
 </head>
 <body>
  <h2>CDR Filter Set</h2>
  <table border='0'>
   <tr>
    <th valign='top' align='right'>Name:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th valign='top' align='right'>Description:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th valign='top' align='right'>Notes:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th valign='top' align='right'>Members:&nbsp;</th>
    <td>
""" % (set.name, set.desc, set.notes)

html += showMembers(set.members)
html += """\
    </td>
   </tr>
  </table>
 </body>
</html>
"""
cdrcgi.sendPage(html)
