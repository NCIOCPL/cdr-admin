#----------------------------------------------------------------------
# Fetch an English summary ready for translation
# BZIssue::4906
# JIRA::OCECDR-4587 - apply revision markup
#----------------------------------------------------------------------

import cgi
import re
import sys
from lxml import etree
from cdrapi.docs import Doc
from cdrapi.users import Session
from cdr import Logging
from cdrcgi import bail
from html import escape as html_escape

CTS = "SummarySection[SectMetaData/SectionType='Changes to summary']"

def show_form():
    """
    Let the user select the document and its version and output format
    """

    print("""\
Content-type: text/html

<html>
 <head>
  <title>CDR Document Display</title>
  <script type="text/javascript">
   function setfocus() {
       document.getElementById("docid").focus();
   }
  </script>
 </head>
 <body style="font-family: Arial, sans-serif" onload="javascript:setfocus()">
  <h1 style="color: maroon">CDR Document Display</h1>
  <form method="POST" action="get-english-summary.py">
   <table>
    <tr>
     <th align="right">Document ID</th>
     <td><input name="id" id="docid" /></td>
    </tr>
    <tr>
     <th align="right">Version</th>
     <td><input name="ver" /></td>
    </tr>
    <tr>
     <th align="right">Output</th>
     <td><input name="format" type="radio" value="display" checked="checked" />
         Display
         <input name="format" type="radio" value="raw" /> Raw
         </td>
    </tr>
   </table>
   <br />
   <input type="submit">
  </form>
  <p style="border: 1px green solid; width: 80%; padding: 5px; color: green">
     Document ID is required, and must be an integer.  Version is optional,
     and can be a positive or negative integer (negative number counts back
     from the most recent version, so -1 means last version, -2 is the one
     before that, etc.).
     If the version is omitted, the current working copy of the document
     is retrieved.  You can also give <i>last</i> for the most recent
     version, or <i>pub</i> for the latest publishable version.  The
     default output is the display of the document in the browser;
     select the "raw" output option to get the XML document itself,
     which you can save to your local file system and pass on to
     Trados for translation.</p>
 </body>
</html>""")

def markup_tag(match):
    """
    Replace XML tags with placeholders

    This is a callback used by `markup()` below, so what we can apply
    color formatting to make the XML tags easier to find and read in
    the display (i.e., not raw) version of the document.

    Pass:
      match - regex SRE_Match object

    Return:
      replacement Unicode string with placeholders for tags
    """

    s = match.group(1)
    if s.startswith("/"):
        return "</@@TAG-START@@{}@@END-SPAN@@>".format(s[1:])
    trailingSlash = ""
    if s.endswith("/"):
        s = s[:-1]
        trailingSlash = "/"
    pieces = re.split("\\s", s, 1)
    if len(pieces) == 1:
        return "<@@TAG-START@@{}@@END-SPAN@@{}>".format(s, trailingSlash)
    tag, attrs = pieces
    pieces = ["<@@TAG-START@@{}@@END-SPAN@@".format(tag)]
    for attr, delim in re.findall("(\\S+=(['\"]).*?\\2)", attrs):
        name, value = attr.split("=", 1)
        pieces.append(" @@NAME-START@@{}=@@END-SPAN@@"
                      "@@VALUE-START@@{}@@END-SPAN@@".format(name, value))
    pieces.append(trailingSlash)
    pieces.append(">")
    return "".join(pieces)

def markup(doc):
    """
    Make the display version easier to view, using color markup

    Pass:
      doc - Unicode string for serialized document XML
    """

    doc = re.sub("<([^>]+)>", markup_tag, doc)
    doc = html_escape(doc)
    doc = doc.replace("@@TAG-START@@", '<span class="tag">')
    doc = doc.replace("@@NAME-START@@", '<span class="name">')
    doc = doc.replace("@@VALUE-START@@", '<span class="value">')
    doc = doc.replace("@@END-SPAN@@", "</span>")
    return doc

def strip(xml):
    """
    Get rid of parts of the document the users don't want to translate

    Pass:
      xml - serialized document string

    Return:
      XML for stripped document
    """

    doomed = ("Comment", "MediaLink", "SectMetaData", "ReplacementFor",
              "PdqKey", "DateLastModified", "ComprehensiveReview", "PMID",
              "BoardMember", "RelatedDocuments", "TypeOfSummaryChange")
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xml, parser)
        first = True
        for node in root.findall("SummaryMetaData/MainTopics"):
            if first:
                first = False
            else:
                parent = node.getparent()
                parent.remove(node)
        for node in root.xpath(CTS):
            parent = node.getparent()
            parent.remove(node)

        etree.strip_elements(root, with_tail=False, *doomed)
        etree.strip_attributes(root, "PdqKey")
        return etree.tostring(root, pretty_print=True, encoding="unicode")
    except Exception as e:
        bail("processing XML document: {}".format(e))

def get_version(session, doc_id, version_string):
    """
    Map a negative version number to the actual version number

    Negative numbers wrap from the end, much the way Python
    sequences do. So -1 means the last version, -2 the penultimate,
    and so on.

    Pass:
      session - Session object for CDR requests
      doc_id - string version for CDR document ID
      version_string - a number, a token (e.g., "last") or an empty string

    Return:
      Integer for actual document version if version_string is a negative int;
      otherwise echo back version_string
    """

    try:
        version_number = int(version_string)
    except:
        return version_string
    if not version_number:
        return None
    elif version_number >= 0:
        return version_number
    try:
        doc = Doc(session, id=docId, version="last")
    except:
        bail("No version found for document {!r}".format(doc_id))
    version = doc.version + version_number + 1
    if version < 1:
        bail("Invalid version number for document {!r}".format(doc_id))
    return version

def fetch_doc(doc_id, version, logger):
    """
    Get the Doc object for the requested document/version

    Pass:
      doc_id - string version for CDR document ID
      version - a number string, a token (e.g., "last") or an empty string
      logger - object for capturing details of failures

    Return:
      `Doc` object
    """

    session = Session("guest")
    version = get_version(session, doc_id, version)
    try:
        doc = Doc(session, id=doc_id, version=version)
        doc.normalize()
        assert doc.xml
        return doc
    except:
        logger.exception("failure loading document")
        message = "Document {!r}".format(doc_id)
        if version:
            message += " version {!r}".format(version)
        message += " not found"
        bail(message)

def filter_doc(doc, logger):
    """
    Apply the standard rules for resolving revision markup

    Changes which have not been marked published or approved will be rejected.

    Pass:
      doc - `Doc` object to be filtered
      logger - object for capturing details of failures

    Return:
      Unicode string for serialization of filtered XML
    """

    try:
        parms = dict(useLevel="2")
        result = doc.filter("name:Revision Markup Filter", parms=parms)
        if isinstance(result.result_tree, etree._Element):
            xml = strip(etree.tostring(result.result_tree, encoding="unicode"))
        else:
            xml = strip(str(result.result_tree))
        return xml
    except:
        logger.exception("failure filtering document")
        bail("failure filtering document")

def send_raw(doc, xml):
    """
    Send the XML document to be given to Trados

    Pass:
      doc - `Doc` object
      xml - Unicode string for serialization of filtered XML
    """

    name = doc.cdr_id
    if doc.version:
        name += "V{:d}".format(doc.version)
    name += ".xml"
    sys.stdout.buffer.write(f"""\
ContentType: text/xml;charset=utf-8
Content-disposition: attachment; filename={name}

{xml}""".encode("utf-8"))

def send_formatted(doc, xml, logger):
    """
    Send the document in a format the user can look at

    Pass:
      doc - `Doc` object
      xml - Unicode string for serialization of filtered XML
      logger - object for capturing details of failures
    """

    try:
        title = "CDR Document {}".format(doc.cdr_id)
        if doc.version:
            title += " (version {:d})".format(doc.version)
        sys.stdout.buffer.write(f"""\
Content-type: text/html;charset=utf-8

<html>
 <head>
  <title>{title}</title>
  <style type="text/css">
.tag {{ color: blue; font-weight: bold }}
.name {{ color: brown }}
.value {{ color: red }}
h1 {{ color: maroon; font-size: 14pt; font-family: Verdana, Arial; }}
  </style>
 </head>
 <body>
  <h1>{title}</h1>
  <pre>{markup(xml)}</pre>
 </body>
</html>""".encode("utf-8"))
    except Exception as e:
        logger.exception("rendering formatted xml")
        bail(e)

def main():
    """
    Top-level processing starts here
    """

    fields = cgi.FieldStorage()
    doc_id = fields.getvalue("id")
    version = fields.getvalue("ver")
    fmt = fields.getvalue("format")
    logger = Logging.get_logger("get-english-summary")
    logger.info("doc_id=%r version=%r format=%r", doc_id, version, fmt)

    if doc_id:
        doc = fetch_doc(doc_id, version, logger)
        xml = filter_doc(doc, logger)
        if fmt == "raw":
            send_raw(doc, xml)
        else:
            send_formatted(doc, xml, logger)
    else:
        show_form()

if __name__ == "__main__":
    main()
