#----------------------------------------------------------------------
#
# $Id: db-tables.py,v 1.1 2006-05-04 14:48:51 bkline Exp $
#
# CGI program to list the CDR tables/views and their structures.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi

class Column:
    def __init__(self, n, t, p, nullable):
        self.name     = n
        self.type     = t
        self.pos      = p
        self.nullable = nullable
        self.pkPos    = None

class Table:
    def __init__(self, cursor, dbName, name, tableType, primaryKeys):
        self.name = name
        self.type = tableType
        self.cols = []
        self.cidx = {}
        cursor.execute("""\
    SELECT COLUMN_NAME, ORDINAL_POSITION, IS_NULLABLE, DATA_TYPE
      FROM %s.INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_NAME = ?
  ORDER BY ORDINAL_POSITION""" % dbName, name)
        for colName, pos, nullable, dataType in cursor.fetchall():
            col = Column(colName, dataType, pos, nullable)
            self.cols.append(col)
            self.cidx[colName] = col
        if primaryKeys:
            for colName in primaryKeys:
                self.cidx[colName].pkPos = primaryKeys[colName]

class Database:
    def __init__(self, cursor, name):
        self.name   = name
        self.tables = {}
        self.views  = {}
        primaryKeys = self.loadPrimaryKeys(cursor)
        cursor.execute("""\
            SELECT TABLE_NAME, TABLE_TYPE
              FROM %s.INFORMATION_SCHEMA.TABLES""" % name)
        for tableName, tableType in cursor.fetchall():
            pks = primaryKeys.get(tableName)
            table = Table(cursor, name, tableName, tableType, pks)
            if tableType.upper() == 'VIEW':
                self.views[tableName] = table
            else:
                self.tables[tableName] = table
    def loadPrimaryKeys(self, cursor):
        cursor.execute("""\
   SELECT U.TABLE_NAME, U.COLUMN_NAME, U.ORDINAL_POSITION
     FROM %s.INFORMATION_SCHEMA.KEY_COLUMN_USAGE U
     JOIN %s.INFORMATION_SCHEMA.TABLE_CONSTRAINTS C
       ON C.CONSTRAINT_NAME = U.CONSTRAINT_NAME
      AND C.TABLE_NAME = U.TABLE_NAME
    WHERE C.CONSTRAINT_TYPE = 'PRIMARY KEY'""" % (self.name, self.name))
        primaryKeys = {}
        for tableName, columnName, ordinalPosition in cursor.fetchall():
            if tableName not in primaryKeys:
                primaryKeys[tableName] = { columnName: ordinalPosition }
            else:
                primaryKeys[tableName][columnName] = ordinalPosition
        return primaryKeys

class Catalog:
    def __init__(self, cursor):
        self.databases = {}
        cursor.execute("""\
    SELECT CATALOG_NAME
    FROM master.INFORMATION_SCHEMA.SCHEMATA""")
        for row in cursor.fetchall():
            try:
                database = Database(cursor, row[0])
                self.databases[database.name] = database
            except:
                pass

def showTables(tables, label, html):
    if tables:
        html.append("<span class='heading'>%s</span>\n" % label)
        tableNames = tables.keys()
        tableNames.sort(lambda a,b: cmp(a.upper(), b.upper()))
        for tableName in tableNames:
            table = tables[tableName]
            html.append("  <span class='tabname'>%s</span>" % tableName)
            for col in table.cols:
                cls = col.pkPos and 'pk' or 'col'
                nul = col.nullable[0] == 'Y' and "NULL" or "NOT NULL"
                val = "%s %s %s" % (col.name, col.type.upper(), nul)
                html.append("     <span class='%s'>%s</span>" % (cls, val))
            html.append("")
        html.append("")

if __name__ == '__main__':
    conn    = cdrdb.connect('CdrGuest')
    cursor  = conn.cursor()
    catalog = Catalog(cursor)
    dbNames = catalog.databases.keys()
    html    = [u"""\
<html>
 <head>
  <title>DB Catalog</title>
  <style type='text/css'>
   .dbname  { color: green; font-size: 16pt; }
   .heading { font-size: 14pt; color: 00DD00; }
   .pk      { color: red; font-size: 10pt; font-style: normal; }
   .col     { color: blue; font-size: 10pt; font-style: normal; }
   .tabname { color: navy; font-size: 12pt; font-weight: bold; }
  </style>
 </head>
 <body>
  <h1>DB Catalog</h1>
  <pre>
"""]
    html.append("<span class='dbname'>cdr DATABASE</span>\n")
    database = catalog.databases['cdr']
    showTables(database.tables, "TABLES", html)
    showTables(database.views, "VIEWS", html)
##     dbNames.sort()
##     for dbName in dbNames:
##         html.append("<span class='dbname'>%s DATABASE</span>\n" % dbName)
##         database = catalog.databases[dbName]
##         showTables(database.tables, "TABLES", html)
##         showTables(database.views, "VIEWS", html)
                


##     table = tables[key]
##     html.append(u"""\
##  <b>%s</b> [%s]""" % (table.name, table.type == 'VIEW' and u"V" or u"T"))
##     for col in table.cols:
##         if col.pkPos:
##             html.append(u"""\
##      <b>%-30s</b> %s""" % (col.name, col.type))
##         else:
##             html.append(u"""\
##      %-30s %s""" % (col.name, col.type))
##     html.append(u"")

html.append(u"""\
  </pre>
 </body>
</html>""")
cdrcgi.sendPage(u"\n".join(html))
