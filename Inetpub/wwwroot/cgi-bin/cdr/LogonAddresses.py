#----------------------------------------------------------------------
# Utility used to track down events when users get confused about
# what they've been doing in the CDR.
#----------------------------------------------------------------------
import cdrdb, re, cgi, cdr, cdrcgi

fields = cgi.FieldStorage()
start  = fields.getvalue('start') or ("%s" % cdr.calculateDateByOffset(-7))
end    = fields.getvalue('end')   or ("%s" % cdr.calculateDateByOffset(0))
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT u.name, u.fullname, s.name, s.initiated, s.ended
      FROM usr u
      JOIN session s
        ON s.usr = u.id
     WHERE s.initiated BETWEEN '%s' AND '%s 23:59:59'
  ORDER BY s.id""" % (start, end), timeout = 300)
rows = cursor.fetchall()
if not rows:
    cdrcgi.bail("no rows for range '%s' to '%s'" % (start, end))
pattern = re.compile("(\\S+ \\S+): Ticket request from (\\S+)")
fp = open('d:/cdr/log/ClientRefresh.log')
lines = fp.read().splitlines()
fp.close()
lines = [line for line in lines if ": Ticket request from " in line and
         line >= rows[0][3]]
pairs = pattern.findall("\n".join(lines))
html = ["""\
<html>
 <head>
  <title>CDR Ticket Request IP Addresses</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
   th, td { font-size: 11pt; border: black solid 1px; }
   th { color: blue; }
   table { border-spacing: 0; border-collapse: collapse; empty-cells: show; }
   h1 { font-size: 14pt; color: maroon; }
   .green { color: green; }
  </style>
 </head>
 <body>
  <h1>CDR Logons and Ticket Requests</h1>
  <table>
   <tr>
    <th>User ID</th>
    <th>User Name</th>
    <th>Session ID</th>
    <th>Logged On</th>
    <th>Logged Off</th>
    <th>Ticket Request</th>
    <th>IP Address</th>
   </tr>
"""]
rowIndex = pairIndex = 0
while rowIndex < len(rows):
    row = rows[rowIndex]
    thisLogon = "%s" % row[3]
    rowIndex += 1
    nextLogon = "3000-01-01"
    if rowIndex < len(rows):
        nextLogon = "%s" % rows[rowIndex][3]
    if pairIndex < len(pairs):
        pair = pairs[pairIndex]
        if pair[0] < nextLogon:
            pairIndex += 1
        else:
            pair = ("", "")
    html.append("""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (row[0], row[1], row[2], row[3],
       row[4] or "<span class='green'>[still logged on]</span>",
       pair[0], pair[1]))
    while pairIndex < len(pairs):
        pair = pairs[pairIndex]
        if pair[0] >= nextLogon:
            break
        html.append("""\
   <tr>
    <td></td>
    <td></td>
    <td></td>
    <td></td>
    <td></td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (pair[0], pair[1]))
        pairIndex += 1
html.append("""\
  </table>
 </body>
</html>""")
print("Content-type: text/html\n")
print("".join(html))
