from pdq_data_partner import Product, Org, Contact
import lxml.etree as etree

Product._load()
root = etree.Element("tables")
for cls in (Product, Org, Contact):
    root.append(cls.to_table_node())
print "Content-type: text/xml"
print
print etree.tostring(root, pretty_print=True)
