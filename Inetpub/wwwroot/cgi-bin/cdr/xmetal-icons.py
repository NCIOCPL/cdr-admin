import glob
import lxml.etree as etree
import lxml.html.builder as B

names = {
    "Annotations": "Annotations (Custom)",
    "Databases": "Databases (Custom)",
    "Design": "Design (Custom)",
    "General": "General (Custom)",
    "Integration": "Integration (Custom)",
    "Misc1": "Misc 1 (Custom)",
    "Misc2": "Misc 2 (Custom)",
    "Revisions": "Revisions (Custom)",
    "Shapes": "Shapes (Custom)",
    "Structure": "Structure (Custom)"
}
css = """\
img { border: 1px black solid }
* { font-family: Arial; }
"""
paths = glob.glob("d:/Inetpub/wwwroot/images/xmetal/*.jpg")
content = B.CENTER(B.H1("XMetaL CDR Icons"))
for path in sorted(paths):
    if "xmetal_cdr" not in path and "Standard" not in path:
        name = path.replace("\\", "/").split("/")[-1][:-4]
        content.append(B.H2(names.get(name, name)))
        content.append(B.IMG(src="/images/xmetal/%s.jpg" % name))
page = B.HTML(
    B.HEAD(
        B.TITLE("XMetaL CDR Icons"),
        B.STYLE(css)
    ),
    B.BODY(content)
)
print "Content-type: text/html\n\n" + etree.tostring(page, pretty_print=True)
