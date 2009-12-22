#----------------------------------------------------------------------
#
# $Id$
#
# Service which provides genetics syndromes used for the GP mailers
# and application form.
#
# BZIssue::4630
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, lxml.etree as etree

class Syndrome:
    def __init__(self, docId, displayName, sortOrder):
        self.docId = docId
        self.displayName = displayName
        self.sortOrder = sortOrder
        self.sortKey = sortOrder or displayName
        self.sortKey = self.sortKey.upper()
    def __cmp__(self, other):
        return cmp(self.sortKey, other.sortKey)
    def toElement(self):
        element = etree.Element('Syndrome', ref='CDR%010d' % self.docId)
        element.text = self.displayName
        return element

def main():
    cursor = cdrdb.connect('CdrGuest').cursor()
    cursor.execute("""\
         SELECT n.doc_id, n.value, o.value
           FROM query_term n
           JOIN query_term t
             ON n.doc_id = t.doc_id
            AND LEFT(n.node_loc, 8) = LEFT(t.node_loc, 8)
           JOIN query_term s
             ON n.doc_id = s.doc_id
            AND LEFT(n.node_loc, 8) = LEFT(s.node_loc, 8)
LEFT OUTER JOIN query_term o
             ON n.doc_id = o.doc_id
            AND LEFT(n.node_loc, 8) = LEFT(o.node_loc, 8)
            AND o.path = '/Term/MenuInformation/MenuItem/@SortOrder'
          WHERE n.path = '/Term/MenuInformation/MenuItem/DisplayName'
            AND t.path = '/Term/MenuInformation/MenuItem/MenuType'
            AND s.path = '/Term/MenuInformation/MenuItem/MenuStatus'
            AND s.value = 'Online'
            AND t.value = 'Genetics Professionals--GeneticSyndrome'""")
    syndromes = [Syndrome(r[0], r[1], r[2]) for r in cursor.fetchall()]
    syndromes.sort()
    root = etree.Element("Syndromes")
    for syndrome in syndromes:
        root.append(syndrome.toElement())
    cdrcgi.sendPage(etree.tostring(root, xml_declaration=True,
                                   encoding='utf-8'), 'xml')

if __name__ == '__main__':
    main()
