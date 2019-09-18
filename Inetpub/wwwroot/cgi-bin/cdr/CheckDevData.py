#!/usr/bin/python

"""Show changes to DEV after DB refresh from PROD.

JIRA::OCECDR-3733
"""

from argparse import ArgumentParser
from cgi import FieldStorage
from difflib import Differ
from glob import glob
from lxml.html import builder
from lxml import html
from cdr import BASEDIR
from cdrapi import db
from cdrcgi import HTMLPage, MAINMENU
from cdr_dev_data import Data

DEV_DATA_PATH = f"{BASEDIR}/DevData"
TITLE = "DEV CDR Refresh Report"
LOST = "DOCUMENT TYPE LOST"
FIXED = builder.CLASS("fixed")
OK = builder.CLASS("ok")
CHECK = "\u2713"
COLORS = {"-": "LightGoldenrodYellow", "+": "Khakhi", "?": "LightSkyBlue"}
RULES = {
    "*": "font-family: Arial, sans-serif;",
    "h1": "color: maroon; font-size: 22pt;",
    "h2": "font-size: 20pt; color: green;",
    "h3": "background-color: green; color: white; padding: 5px;",
    "p.ok": "font-size: 16pt; padding-left: 30px;",
    "pre.fixed, pre.fixed span": "font-family: monospace; font-size: 9pt;",
    "input.path": "width: 500px;",
}
RULES = "\n".join([f"{sel} {{ {rules} }}" for (sel, rules) in RULES.items()])
HEAD = builder.HEAD(
    builder.META(charset="utf-8"),
    builder.TITLE(TITLE),
    builder.STYLE(RULES),
)

def compare_table(body, name, old, new):
    items = []
    ot = old.tables[name]
    nt = new.tables[name]
    if set(ot.cols) != set(nt.cols):
        ul = builder.UL()
        item = builder.LI("TABLE STRUCTURE MISMATCH", ul)
        ul.append(builder.LI(f"old: {ot.cols:!r}"))
        ul.append(builder.LI(f"new: {nt.cols:!r}"))
        items.append(item)
    if ot.names:
        for key in sorted(ot.names):
            if key not in nt.names:
                items.append(builder.LI("row for ", builder.B(key), " lost"))
                continue
            old_row = ot.names[key].copy()
            new_row = nt.names[key].copy()
            if "id" in old_row:
                old_row.pop("id")
                new_row.pop("id")
            if old_row != new_row:
                cols = builder.UL()
                item = builder.LI("row for ", builder.B(key), " changed", cols)
                items.append(item)
                for col in old_row:
                    ov = old_row[col]
                    nv = new_row[col]
                    if ov != nv:
                        if name == "query" and col == "value":
                            ov = builder.PRE(ov.replace("\r", ""))
                            nv = builder.PRE(nv.replace("\r", ""))
                        else:
                            ov = repr(ov)
                            nv = repr(nv)
                        changes = builder.LI(f"{col!r} column changed")
                        cols.append(changes)
                        if col not in ("hashedpw", "password"):
                            changes.append(builder.UL(
                                builder.LI(f"old: {ov}"),
                                builder.LI(f"new: {nv}")
                            ))
    elif name in ("grp_action", "grp_usr"):
        old_rows = [getattr(old, name)(row) for row in ot.rows]
        new_rows = [getattr(new, name)(row) for row in nt.rows]
        for row in sorted(set(old_rows) - set(new_rows)):
            items.append(builder.LI(f"row for {row} lost"))
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
        try:
            for row, which_set in sorted(deltas, key=lambda v:str(v)):
                items.append(builder.LI(f"{which_set}: {row}"))
        except:
            print(deltas)
            raise
    if items:
        body.append(builder.UL(*items))
    else:
        body.append(builder.P(CHECK, OK))

def compare_tables(body, old, new):
    body.append(builder.H2("Table Comparisons"))
    for name in sorted(old.tables):
        body.append(builder.H3(name))
        if name in new.tables:
            compare_table(body, name, old, new)
        else:
            body.append(builder.UL(builder.LI(builder.B("TABLE LOST"))))

def diff_xml(old, new, verbose=False):
    differ = Differ()
    before = old.replace("\r", "").splitlines()
    after = new.replace("\r", "").splitlines()
    diffs = differ.compare(before, after)
    lines = []
    changes = False
    for line in diffs:
        line = line.rstrip("\n")
        color = COLORS.get(line[0], "white")
        if line and line[0] in COLORS:
            changes = True
            bgcolor = f"background-color: {color}"
            span = builder.SPAN(f"{line}\n", style=bgcolor)
            lines.append(span)
        elif verbose:
            lines.append(builder.SPAN(line))
    if changes:
        return builder.PRE(FIXED, *lines)
    return None

def compare_docs(body, old, new, verbose):
    body.append(builder.H2("Document Comparisons"))
    for name in sorted(old.docs):
        body.append(builder.H3(f"{name} Docs"))
        new_docs = new.docs[name]
        if not new_docs.docs:
            body.append(builder.UL(builder.LI(builder.B(LOST))))
        else:
            old_docs = old.docs[name]
            items = []
            for key in old_docs.docs:
                old_id, old_title, old_xml = old_docs.docs[key]
                if key not in new_docs.docs:
                    items.append(builder.I(builder.LI(old_title)))
                else:
                    diffs = diff_xml(old_xml, new_docs.docs[key][2], verbose)
                    if diffs is not None:
                        title = builder.B(old_title)
                        items.append(builder.LI(title, diffs))
            if not items:
                body.append(builder.P(CHECK, OK))
            else:
                body.append(builder.UL(*items))

fields = FieldStorage()
parser = ArgumentParser()
parser.add_argument("--old", default=fields.getvalue("path"))
parser.add_argument("--new", default=db.connect(user="CdrGuest").cursor())
parser.add_argument("--verbose", action="store_true")
opts = parser.parse_args()
if opts.old:
    old = Data(opts.old)
    new = Data(opts.new, old)
    body = builder.BODY(builder.H1(TITLE))
    compare_tables(body, old, new)
    compare_docs(body, old, new, opts.verbose)
    report = builder.HTML(HEAD, body)
    print("Content-type: text/html; charset=utf-8\n")
    opts = dict(pretty_print=True, doctype="<!DOCTYPE html>")
    print(html.tostring(report, pretty_print=True).decode("ascii"))
else:
    buttons = HTMLPage.button("Submit"), HTMLPage.button(MAINMENU)
    page = HTMLPage(TITLE, buttons=buttons)
    fieldset = page.fieldset("Saved Development Server Date")
    files = glob(f"{DEV_DATA_PATH}/DevData-20*")
    default = sorted(files)[-1].replace("\\", "/") if files else DEV_DATA_PATH
    fieldset.append(page.text_field("path", value=default))
    page.form.append(fieldset)
    page.send()
