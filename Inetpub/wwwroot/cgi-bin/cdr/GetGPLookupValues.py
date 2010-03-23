#----------------------------------------------------------------------
#
# $Id: GetGeneticsSyndromes.py 9444 2009-12-22 15:07:28Z bkline $
#
# Service which provides lookup values for GP mailers and application forms.
#
# BZIssue::4630
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, lxml.etree as etree

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
        element = etree.Element('Value', ref='CDR%010d' % self.docId)
        element.text = self.displayName.strip()
        return element

def getValues(vvLists, key, setType):
    other = False
    valueSet = etree.Element("ValueSet", type=setType)
    values = [value.strip() for value in vvLists[key]]
    values.sort()
    for value in values:
        if value == 'Other':
            other = True
        else:
            element = etree.Element('Value')
            element.text = value
            valueSet.append(element)
    if other:
        element = etree.Element('Value')
        element.text = 'Other'
        valueSet.append(element)
    return valueSet

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
    root = etree.Element('ValueSets')
    valueSet = etree.Element("ValueSet", type='Syndromes')
    for syndrome in syndromes:
        valueSet.append(syndrome.toElement())
    root.append(valueSet)
    docType = cdr.getDoctype('guest', 'Person')
    vvLists = dict(docType.vvLists)
    root.append(getValues(vvLists, 'ProfessionalType', 'ProfessionalTypes'))
    root.append(getValues(vvLists, 'GeneticsTeamServices', 'TeamServices'))
    root.append(getValues(vvLists, 'MemberOfGeneticsSociety', 'Societies'))
    root.append(getValues(vvLists, 'GeneticsBoardName', 'Specialties'))
    cdrcgi.sendPage(etree.tostring(root, xml_declaration=True,
                                   encoding='utf-8'), 'xml')

if __name__ == '__main__':
    main()
