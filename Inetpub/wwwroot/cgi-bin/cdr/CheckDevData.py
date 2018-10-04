#!/usr/bin/python
"""
Show changes to DEV after DB refresh from PROD

JIRA::OCECDR-3733
"""

import cgi
import difflib
import sys
import cdrdb
import cdr_dev_data

PROLOG = """\
<!DOCTYPE html>
<html>
 <head>
  <meta charset="utf-8">
  <title>DEV CDR Refresh Report</title>
  <style>
  * { font-family: Arial, sans-serif }
  h1 { color: maroon; font-size: 22pt; }
  h2 { font-size: 20pt; color: green; }
  h3 { background-color: green; color: white; padding: 5px; }
  p.ok { font-size: 16pt; padding-left: 30px; }
  pre.fixed, pre.fixed span { font-family: monospace; font-size: 9pt; }
  input.path { width: 500px; }
  </style>
 </head>
 <body>
  <h1>DEV CDR Refresh Report</h1>"""
EPILOG = """\
 </body>
</html>"""
FORM = """\
%s
  <form action="CheckDevData.py">
   <label for="path">Path to Preserved DEV Data:&nbsp;</label>
   <input class="path" name="path" id="path">
   <br><br>
   <input type="submit" value="Request Report">
  </form>
%s""" % (PROLOG, EPILOG)

def fix_para(p):
    p = cgi.escape(p).replace("\r", "").replace("\n", "<br>")
    return (u"<pre class='fixed'>%s</pre>" % p).encode("utf-8")

def compare_table(name, old, new):
    items = []
    ot = old.tables[name]
    nt = new.tables[name]
    if set(ot.cols) != set(nt.cols):
        items.append("TABLE STRUCTURE MISMATCH"
                     "<li>old: %s</li><li>new: %s</li></ul>" %
                     (repr(ot.cols), repr(nt.cols)))
    if ot.names:
        for key in sorted(ot.names):
            display = "<b>%s</b>" % cgi.escape(key)
            if key not in nt.names:
                items.append("row for %s lost" % display)
                continue
            old_row = ot.names[key].copy()
            new_row = nt.names[key].copy()
            if "id" in old_row:
                old_row.pop("id")
                new_row.pop("id")
            if old_row != new_row:
                change = ["row for %s changed<ul>" % display]
                for col in old_row:
                    ov = old_row[col]
                    nv = new_row[col]
                    if ov != nv:
                        if name == "query" and col == "value":
                            ov = fix_para(ov)
                            nv = fix_para(nv)
                        else:
                            ov = repr(ov)
                            nv = repr(nv)
                        change.append("<li>'%s' column changed" % col)
                        if col not in ("hashedpw", "password"):
                            change.append("<ul><li>old: %s</li>" % ov)
                            change.append("<li>new: %s</li></ul>" % nv)
                        change.append("</li>")
                change.append("</ul>")
                items.append("".join(change))
    elif name in ("grp_action", "grp_usr"):
        old_rows = [getattr(old, name)(row) for row in ot.rows]
        new_rows = [getattr(new, name)(row) for row in nt.rows]
        for row in sorted(set(old_rows) - set(new_rows)):
            items.append((u"row for %s lost" % cgi.escape(row)).encode("utf-8"))
    else:
        if name in dir(old):
            old_rows = set([getattr(old, name)(row) for row in ot.rows])
            new_rows = set([getattr(new, name)(row) for row in nt.rows])
        else:
            old_rows = set(ot.rows)
            new_rows = set(nt.rows)
        old_only = [(row, "lost") for row in (old_rows - new_rows)]
        new_only = [(row, "added") for row in (new_rows - old_rows)]
        deltas = old_only + new_only
        for row, which_set in sorted(deltas):
            items.append("%s: %s" % (which_set, row))
    if not items:
        print """<p class="ok">&#x2713;</p>"""
    else:
        print "  <ul>\n   "
        print "\n   ".join(["<li>%s</li>" % i for i in items])
        print "\n  </ul>"

def compare_tables(old, new):
    print "  <h2>Table Comparisons</h2>"
    for name in sorted(old.tables):
        print "  <h3>%s</h3>" % name
        if name in new.tables:
            compare_table(name, old, new)
        else:
            print "  <ul><li><b>TABLE LOST</b></li></ul>"

def fix_xml(x):
    # This didn't work so well for our XSL/T filters, which have lots of
    # attributes which span multiple lines.
    #x = etree.tostring(etree.XML(x.encode("utf-8")), pretty_print=True)
    lines = x.replace("\r", "").splitlines(1)
    return lines

def addColor(line, color):
    return "<span style='background-color: %s'>%s</span>" % (color, line)

def diff_xml(old, new):
    diffObj = difflib.Differ()
    before = fix_xml(old)
    after = fix_xml(new)
    diffSeq = diffObj.compare(before, after)
    lines = []
    changes = False
    for line in diffSeq:
        line = cgi.escape(line)
        if not line.startswith(' '):
            changes = True
        if line.startswith('-'):
            lines.append(addColor(line, '#FAFAD2')) # Light goldenrod yellow
        elif line.startswith('+'):
            lines.append(addColor(line, '#F0E68C')) # Khaki
        elif line.startswith('?'):
            lines.append(addColor(line, '#87CEFA')) # Light sky blue
        #else: # uncomment these lines if you want a *really* wordy report!
        #    lines.append(line)
    if not changes:
        return None
    return "".join(lines)

def compare_docs(old, new):
    print "  <h2>Document Comparisons</h2>"
    for name in sorted(old.docs):
        print "  <h3>%s Docs</h3>" % name
        new_docs = new.docs[name]
        if not new_docs.docs:
            print "  <ul><li><b>DOCUMENT TYPE LOST</b></li></ul>"
        else:
            old_docs = old.docs[name]
            items = []
            for key in old_docs.docs:
                old_id, old_title, old_xml = old_docs.docs[key]
                if key not in new_docs.docs:
                    items.append("<i>%s</i> lost" % cgi.escape(old_title))
                else:
                    diffs = diff_xml(old_xml, new_docs.docs[key][2])
                    if diffs:
                        show = ["<b>%s</b>" % cgi.escape(old_title)]
                        show.append("<pre class='fixed'>%s</pre>" % diffs)
                        items.append("".join(show))
            if not items:
                print "<p class='ok'>&#x2713;</p>"
            else:
                print "  <ul>"
                print "   " + "\n   ".join(["<li>%s</li>" % i.encode("utf-8")
                                            for i in items])
                print "  </ul>"

if len(sys.argv) > 1:
    old_source = sys.argv[1]
    if len(sys.argv) > 2:
        new_source = sys.argv[2]
    else:
        new_source = cdrdb.connect("CdrGuest").cursor()
else:
    print "Content-type: text/html; charset=utf-8\n"
    fields = cgi.FieldStorage()
    old_source = fields.getvalue("path")
    if not old_source:
        print FORM
        sys.exit(0)
    new_source = cdrdb.connect("CdrGuest").cursor()
old = cdr_dev_data.Data(old_source)
new = cdr_dev_data.Data(new_source, old)
print PROLOG
compare_tables(old, new)
compare_docs(old, new)
print EPILOG
