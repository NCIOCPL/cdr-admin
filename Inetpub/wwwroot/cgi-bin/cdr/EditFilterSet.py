#----------------------------------------------------------------------
# Form for editing named CDR filter sets.
#
# BZIssue::3716 - Unicode encoding cleanup
# Rewritten August 2015 as part of security sweep.
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# Import required modules.
#----------------------------------------------------------------------
import cdr
import cdrdb
import cdrcgi
import cgi
import re

#----------------------------------------------------------------------
# Set some initial values.
#----------------------------------------------------------------------
banner   = "CDR Filter Set Editing"
title    = "Edit CDR Filter Set"
SUBMENU  = "Filter Sets"
REQUESTS = ("Log Out", cdrcgi.MAINMENU, SUBMENU, "Edit", "New")

#----------------------------------------------------------------------
# Load the fields from the form.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
if not fields: cdrcgi.bail("Unable to read form fields", banner)
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
setName    = fields.getvalue('setName') or ''
newName    = fields.getvalue('newName') or ''
setDesc    = fields.getvalue('setDesc') or ''
setNotes   = fields.getvalue('setNotes') or ''
setMembers = fields.getvalue('setMembers') or ''
isNew      = fields.getvalue('isNew') or 'N'
doWhat     = fields.getvalue('doWhat') or ''
noMembers  = "<< No members currently assigned to the set >>"
filterSets = cdr.getFilterSets('guest')

#----------------------------------------------------------------------
# Make sure we're allowed.
#----------------------------------------------------------------------
def allowed(session):
    for action in ("ADD FILTER SET", "MODIFY FILTER SET", "DELETE FILTER SET"):
        if cdr.canDo(session, action):
            return True
    return False
if not allowed(session):
    cdrcgi.bail("Account not permitted to use this page", banner)

#----------------------------------------------------------------------
# Do some sanitizing of the parameters. The setDesc, setNotes, and
# newName strings are escaped when inserted into HTML or CDR commmand
# XML strings, and SQL placeholders are used in all of the database
# queries which use the values.
#----------------------------------------------------------------------
if doWhat and doWhat not in ("Save", "Delete", "?"):
    cdrcgi.bail()
if isNew not in ("Y", "N"):
    cdrcgi.bail()
if request and request not in REQUESTS:
    cdrcgi.bail()
if setDesc and len(setDesc) > 256:
    cdrcgi.bail("Set description cannot exceed 256 characters")
if newName:
    if len(newName) > 80:
        cdrcgi.bail("Set name cannot exceed 80 characters")
    try:
        newName.decode("ascii")
    except:
        cdrcgi.bail("Set name must contain ASCII characters only")
if setName and setName not in set([s.name for s in filterSets]):
    cdrcgi.bail()
if setMembers:
    for m in setMembers.split("|"):
        if not m or m[0] not in ("S", "F"):
            cdrcgi.bail()
        memberId = m[1:]
        if not memberId or not memberId.isdigit():
            cdrcgi.bail()

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("EditFilterSets.py", session)

#----------------------------------------------------------------------
# Get the CDR filters and wrap them in <option> elements.
#----------------------------------------------------------------------
def getFilters():
    html = u""
    filters = cdr.getFilters('guest')
    for filter in filters:
        if len(filter.name) and filter.name[0] != '[':
            id   = int(re.sub(r'[^\d]', '', filter.id))
            name = cgi.escape(filter.name[:60])
            html += u"<option value='%d'>%s</option>\n" % (id, name)
    for filter in filters:
        if len(filter.name) and filter.name[0] == '[':
            id   = int(re.sub(r'[^\d]', '', filter.id))
            name = cgi.escape(filter.name[:60])
            html += u"<option value='%d'>%s</option>\n" % (id, name)
    return html

#----------------------------------------------------------------------
# Get the CDR filter sets and wrap them in <option> elements.
#----------------------------------------------------------------------
def getFilterSets():
    html = u""
    for filterSet in filterSets:
        id   = filterSet.id
        name = cgi.escape(filterSet.name[:60])
        html += u"<option value='%d'>%s</option>\n" % (id, name)
    return html

#----------------------------------------------------------------------
# Create the initial <option/> elements for the set's members.
#----------------------------------------------------------------------
def getSetMemberHtml(members = None):
    html = u""
    if not members:
        html = u"<option value='0'>%s</option>" % cgi.escape(noMembers, 1)
    else:
        for member in members:
            id = member.id
            name = cgi.escape(member.name)
            if type(id) == type(9):
                name = u"[S]%s" % name
                value = u"S%d" % id
            else:
                name = u"[F]%s" % name
                id = int(re.sub(r'[^\d]', '', id))
                value = u"F%d" % id
            html += u'<option value="%s">%s</option>\n' % (value, name)
    return html

#----------------------------------------------------------------------
# Create the JavaScript function for deleting the set.  The behavior
# of the function depends on whether the set can be deleted (it can't
# if it's being used as a nested member of other sets).
#----------------------------------------------------------------------
def makeDelFunction():
    if not setName: return "return;\n"
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
              SELECT ps.name
                FROM filter_set ms
                JOIN filter_set_member m
                  ON m.subset = ms.id
                JOIN filter_set ps
                  ON m.filter_set = ps.id
               WHERE ms.name = ?
            ORDER BY ps.name""", setName)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Database failure finding nested memberships: %s" %
                info[1][0])
    if rows:
        body = u"""\
        alert("Filter set cannot be deleted; it is used as a member of:"""
        for row in rows:
            body += '\\n"\n            + "%s' % row[0]
        return body + '");\n';
    else:
        return u"""\
        response = confirm("Are you sure you want to delete %s?");
        if (response) {
            var frm = document.forms[0];
            frm.doWhat.value = 'Delete';
            frm.submit();
        }
""" % cdrcgi.unicodeToJavaScriptCompatible(cdr.toUnicode(setName))

#----------------------------------------------------------------------
# Display the CDR document form.
#----------------------------------------------------------------------
def showForm(isNew, members = None):
    html = u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Edit CDR Filter Set</title>
  <meta http-equiv="Content-type" content="text/html;charset=utf-8" />
  <basefont face='Arial, Helvetica, sans-serif'>
  <link rel='stylesheet' href='/stylesheets/dataform.css'>
  <script language='JavaScript'>
    function doSave() {
        var frm = document.forms[0];
        var setDesc = frm.setDesc.value;
        if (!setDesc) {
            alert('Set Description is required.');
            return;
        }
        var numOpts = frm.members.options.length;
        var sep = '';
        var sm = frm.setMembers;
        sm.value = '';
        for (var i = 0; i < numOpts; ++i) {
            if (frm.members.options[i].value != '0') {
                sm.value += sep + frm.members.options[i].value;
                sep = '|';
            }
        }
        frm.doWhat.value = 'Save';
        frm.submit();
    }
    function doDelete() {
        %s
    }
    function blockChange() {
        %s
        var frm = document.forms[0];
        frm.elements.newName.value = "%s";
    }
    function addFilter() {
        var frm    = document.forms[0];
        var i      = frm.filters.selectedIndex;
        if (i < 0) return;
        var filter = frm.filters[i];
        var opt    = new Option('[F]' + filter.text, 'F' + filter.value);
        var n      = frm.members.options.length;
        opt.selected = true;
        frm.members.options[n] = opt;
        if (frm.members.options[0].value == 0) {
            frm.members.options[0] = null;
        }
    }
    function addFilterSet() {
        var frm      = document.forms[0];
        var i        = frm.filterSets.selectedIndex;
        if (i < 0) return;
        var set      = frm.filterSets[i];
        var opt      = new Option('[S]' + set.text, 'S' + set.value);
        var n        = frm.members.options.length;
        opt.selected = true;
        frm.members.options[n] = opt;
        if (frm.members.options[0].value == 0) {
            frm.members.options[0] = null;
        }
    }
    function moveUp() {
        var frm     = document.forms[0];
        var members = frm.members;
        var options = members.options;
        var i       = members.selectedIndex;
        if (i > 0) {
            var o1 = options[i - 1];
            var o2 = options[i];
            var opt1 = new Option(o1.text, o1.value);
            var opt2 = new Option(o2.text, o2.value);
            options[i - 1] = opt2;
            options[i] = opt1;
            options[i - 1].selected = true;
        }
    }
    function moveDown() {
        var members = document.forms[0].members;
        var opts    = members.options;
        var i       = members.selectedIndex
        if (i >= 0 && i < opts.length - 1) {
            var o1 = opts[i + 1];
            var o2 = opts[i];
            var opt1 = new Option(o1.text, o1.value);
            var opt2 = new Option(o2.text, o2.value);
            opts[i + 1] = opt2;
            opts[i] = opt1;
            opts[i + 1].selected = true;
        }
    }
    function deleteMember() {
        var frm = document.forms[0];
        var i   = frm.members.selectedIndex;
        if (i >= 0) {
            frm.members.options[i] = null;
            if (frm.members.options.length == 0) {
                var opt = new Option("%s", 0);
                frm.members.options[0] = opt;
            }
            else {
                if (i == frm.members.options.length)
                    --i;
                frm.members.options[i].selected = true;
            }
        }
    }
  </script>
 </head>
 <body bgcolor='EEEEEE'>
  <form action='/cgi-bin/cdr/EditFilterSet.py' method='POST'>
   <table width='100%%' cellspacing='0' cellpadding='0' border='0'>
    <tr>
     <th nowrap bgcolor='silver' align='left' background='/images/nav1.jpg'>
      <font size='6' color='white'>&nbsp;CDR Filter Set Editing</FONT>
     </th>
     <td bgcolor='silver'
         valign='middle'
         align='right'
         width='100%%'
         background='/images/nav1.jpg'>
      <input type='button' name='SaveSet' value='Save Set' onClick='doSave();'>
       &nbsp;
       %s
      <input type='submit' name='Request' value="%s">&nbsp;
      <input type='submit' name='Request' value="%s">&nbsp;
      <input type='submit' name='Request' value='Log Out'>&nbsp;
     </td>
    </tr>
    <tr>
     <td bgcolor='#FFFFCC' colspan='3'>
      <font size='-1' color='navy'>&nbsp;Edit CDR Filter Set<br></font>
     </td>
    </tr>
   </table>
   <br>
   <table border='0'>
    <tr>
     <td align='right' nowrap=1><b>Set Name:</b>&nbsp;</td>
     <td>
      <input name='newName' size='80' value="%s" onChange='blockChange()'>
     </td>
    </tr>
    <tr>
     <td align='right' nowrap=1><b>Set Description:</b>&nbsp;</td>
     <td><input name='setDesc' value="%s" size='80'></td>
    </tr>
    <tr>
     <td align=right nowrap=1><b>Set Notes:</b>&nbsp;</td>
     <td><textarea name='setNotes' rows='5' cols='60'>%s</textarea></td>
    </tr>
   </table>
   <table border='0'>
    <tr>
     <td align='center'>
      <b>Set Membership</b>
     </td>
     <td align='center'>
      <b>Filters</b>
     </td>
     <td align='center'>
      <b>Filter Sets</b>
     </td>
    </tr>
    <tr>
     <td>
      <select name='members' size='20'>
       %s
      </select>
     </td>
     <td>
      <select name='filters' size='20' onDblClick='addFilter()'>
       %s
      </select>
     </td>
     <td colspan='2' align='center'>
      <select name='filterSets' size='20' onDblClick='addFilterSet()'>
       %s
      </select>
     </td>
    </tr>
    <tr>
     <td align='center'>
      <input type='button' onClick='moveUp()' value = 'Move Up'/>
      <input type='button' onClick='moveDown()' value = 'Move Down'/>
      <input type='button' onClick='deleteMember()' value = 'Delete'/>
     </td>
     <td>&nbsp;</td>
     <td>&nbsp;</td>
    </tr>
    <!--
    <tr>
     <td colspan='2' align='center'>
      <b>Filter Sets</b>
     </td>
    </tr>
    <tr>
    </tr>
    -->
   </table>
   <input type='hidden' name='setMembers' value=''>
   <input type='hidden' name="%s" value="%s">
   <input type='hidden' name='isNew' value="%s">
   <input type='hidden' name='doWhat' value="?">
   <input type='hidden' name='setName' value="%s">
  </form>
 </body>
</html>
""" % (makeDelFunction(),
       isNew == 'Y' and "return;" or "",
       setName and cgi.escape(cdr.toUnicode(setName), 1) or '',
       noMembers,
       isNew != 'Y' and """\
      <input type='button' name='DelSet' value='Delete Set'
             onClick='doDelete();'>
       &nbsp;
""" or "",
       SUBMENU,
       cdrcgi.MAINMENU,
       setName and cgi.escape(cdr.toUnicode(setName), 1) or '',
       setDesc and cgi.escape(setDesc, 1) or '',
       setNotes and cgi.escape(setNotes, 1) or '',
       getSetMemberHtml(members),
       getFilters(),
       getFilterSets(),
       cdrcgi.SESSION,
       session,
       isNew,
       setName and cgi.escape(cdr.toUnicode(setName), 1) or '')
    cdrcgi.sendPage(html)

#----------------------------------------------------------------------
# Edit an existing filter set.
#----------------------------------------------------------------------
if request == 'Edit':
    filterSet = cdr.getFilterSet('guest', cdr.toUnicode(setName))
    setDesc = filterSet.desc
    setNotes = filterSet.notes
    showForm('N', filterSet.members)

#----------------------------------------------------------------------
# Create a new filter set.
#----------------------------------------------------------------------
if request == 'New':
    showForm('Y')

#----------------------------------------------------------------------
# Delete the filter set.
#----------------------------------------------------------------------
if doWhat == 'Delete':
    if not cdr.canDo(session, "DELETE FILTER SET"):
        cdrcgi.bail("Action not permitted for this account.")
    try:
        cdr.delFilterSet(session, cdr.toUnicode(setName))
    except StandardError, args:
        cdrcgi.bail("Failure deleting filter set")
    except UnicodeDecodeError, args:
        cdrcgi.bail(u"Unicode decode error deleting filter set")
    except:
        cdrcgi.bail("Unknown failure deleting filter set")
    cdrcgi.navigateTo("EditFilterSets.py", session)

#----------------------------------------------------------------------
# Save the filter set.
#----------------------------------------------------------------------
if doWhat == 'Save':
    setMemberList = []
    if setMembers:
        for member in setMembers.split('|'):
            idInt = int(member[1:])
            if member[0] == 'F':
                setMemberList.append(cdr.IdAndName("CDR%010d" % idInt, ""))
            else:
                setMemberList.append(cdr.IdAndName(idInt, ""))
    if isNew == 'Y':
        if not cdr.canDo(session, "ADD FILTER SET"):
            cdrcgi.bail("Action not permitted for this account.")
        newSet = cdr.FilterSet(newName, setDesc, setNotes, setMemberList)
        try:
            cdr.addFilterSet(session, newSet)
        except StandardError, args:
            cdrcgi.bail("Failure adding new filter set")
        except UnicodeDecodeError, args:
            cdrcgi.bail(u"Unicode decode error saving new filter set")
        except:
            cdrcgi.bail("Unknown failure adding new filter set")
        setName = newName
    else:
        if not cdr.canDo(session, "MODIFY FILTER SET"):
            cdrcgi.bail("Action not permitted for this account.")
        oldSet = cdr.FilterSet(setName, setDesc, setNotes, setMemberList)
        try:
            cdr.repFilterSet(session, oldSet)
        except StandardError, args:
            cdrcgi.bail(u"Failure storing changes to filter set")
        except UnicodeDecodeError, args:
            cdrcgi.bail(u"Unicode decode error updating filter set")
        except:
            cdrcgi.bail("Unknown failure storing changes to filter set")

    filterSet = cdr.getFilterSet('guest', cdr.toUnicode(setName))
    setDesc = filterSet.desc
    setNotes = filterSet.notes
    showForm('N', filterSet.members)

#----------------------------------------------------------------------
# Tell the user we don't know how to do what he asked.
#----------------------------------------------------------------------
else: cdrcgi.bail("Request not yet implemented: " + request, banner)
