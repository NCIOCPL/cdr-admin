#----------------------------------------------------------------------
#
# $Id$
#
# Report on external mappings to documents of the wrong type.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi, xml.sax.saxutils

def fix(me):
    return me and xml.sax.saxutils.escape(me) or u""

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("SELECT id, name FROM external_map_usage")
usageNames = {}
for usageId, usageName in cursor.fetchall():
    usageNames[usageId] = usageName
cursor.execute("SELECT id, name FROM doc_type")
typeNames = {}
for typeId, typeName in cursor.fetchall():
    typeNames[typeId] = typeName
cursor.execute("SELECT usage, doc_type FROM external_map_type")
usageTypes = {}
for mapId, mapType in cursor.fetchall():
    if mapId in usageTypes:
        usageTypes[mapId][mapType] = typeNames[mapType]
    else:
        usageTypes[mapId] = { mapType: typeNames[mapType] }
cursor.execute("""\
    SELECT m.id, m.usage, m.value, m.doc_id, t.name
      FROM external_map m
      JOIN document d
        ON m.doc_id = d.id
      JOIN doc_type t
        ON d.doc_type = t.id
     WHERE t.id NOT IN (SELECT doc_type
                          FROM external_map_type
                         WHERE usage = m.usage)""")
html = [u"""\
<html>
 <head>
  <title>Bad ExternalMappings</title>
  <style type='text/css'>
   body {font-family: Arial}
  </style>
 </head>
 <body>
  <h1>Bad External Mappings</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Usage</th>
    <th>Value</th>
    <th>DocID</th>
    <th>DocType</th>
    <th>Allowed</th>
   </tr>"""]

def allowed(usageId):
    if usageId not in usageTypes:
        return u"None"
    types = usageTypes[usageId]
    return u", ".join([types[i] for i in types])

for row in cursor.fetchall():
    html.append(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
   </tr>""" % (usageNames[row[1]], fix(row[2]), row[3], row[4],
               allowed(row[1])))
html.append(u"""\
  </table>
 </body>
</html>""")
cdrcgi.sendPage(u"\n".join(html))
