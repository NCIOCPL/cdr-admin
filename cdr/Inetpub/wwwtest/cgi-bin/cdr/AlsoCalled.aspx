<%--
  ======================================================================
  $Id: AlsoCalled.aspx,v 1.2 2006-12-12 03:12:26 bkline Exp $

  Report for Margaret showing related glossary terms (see request #2565).

  $Log: not supported by cvs2svn $
  Revision 1.1  2006/12/12 03:04:17  bkline
  Second report for request #2685.

  ======================================================================
  --%>
<%@ Page Language='C#' Debug='True' %>
<%@ Import Namespace='System.Data' %>
<%@ Import Namespace='System.Data.SqlClient' %>
<%@ Import Namespace='System.Collections' %>
<%@ Import Namespace='System.Text.RegularExpressions' %>

<script runat='server'>
    public class GlossaryTerm {
        public int docId;
        public string name;
        public bool done;
        public ArrayList otherNames;
        public static Regex pattern = new Regex("(.+) (and|or) (.+)",
                                                RegexOptions.Singleline);
        public GlossaryTerm(string name, int docId) {
            this.name = name;
            this.docId = docId;
            this.done = false;
            this.otherNames = new ArrayList();
        }
        public virtual void addRow(HtmlTable table, int nCols) {
            object[] values = new object[nCols];
            values[0] = this.docId;
            values[1] = this.name;
            this.otherNames.Sort();
            this.otherNames.CopyTo(values, 2);
            GlossaryTerm.addRow(table, values);
        }
        protected static void addRow(HtmlTable table, object[] values) {
            HtmlTableRow row = new HtmlTableRow();
            table.Rows.Add(row);
            foreach (object value in values) { 
                HtmlTableCell cell = new HtmlTableCell();
                string text = "";
                if (value != null)
                    text = value.ToString().Trim();
                if (text.Length == 0)
                    text = "\u00A0";
                cell.InnerText = text;
                row.Cells.Add(cell);
            }
        }
        private void addOtherName(string word) {
            string w = word.Trim();
            w = w.TrimEnd(",".ToCharArray());
            string ucWord = w.ToUpper();
            if (ucWord.StartsWith("A "))
                w = w.Substring(2).Trim();
            else if (ucWord.StartsWith("AN "))
                w = w.Substring(3).Trim();
            else if (ucWord.StartsWith("THE "))
                w = w.Substring(4).Trim();
            w = w.Trim();
            if (w.Length > 0) {
                this.otherNames.Add(w);
            }
        }
        public int extractOtherNames(string def) {
            string d = def.Replace("\n\r", " ").Replace("\n", " ")
                          .Replace("\r", " ").TrimEnd(".".ToCharArray());
            string ucDef = d.ToUpper();
            string label = "ALSO CALLED";
            int pos = ucDef.IndexOf(label);
            if (pos > -1) {
                string also = d.Substring(pos + label.Length);
                Match match = GlossaryTerm.pattern.Match(also);
                if (match.Success) {
                    string before = match.Groups[1].ToString();
                    string after  = match.Groups[3].ToString();
                    int index = before.IndexOf(", ");
                    while (index > -1) {
                        addOtherName(before.Substring(0, index));
                        before = before.Substring(index + 2);
                        index = before.IndexOf(", ");
                    }
                    addOtherName(before);
                    addOtherName(after);
                }
                else
                    addOtherName(also);
            }
            return this.otherNames.Count;
        }
    }
    public class DuplicateTerm : GlossaryTerm {
        GlossaryTerm otherTerm;
        public DuplicateTerm(string name, 
                      int docId, 
                      GlossaryTerm otherTerm) : base(name, docId) {
            this.otherTerm = otherTerm;
        }
        public virtual void addRow(HtmlTable table) {
            GlossaryTerm.addRow(table, new object[] { this.docId, this.name,
                                                      this.otherTerm.docId,
                                                      this.otherTerm.name });
        }
    }
    void Page_Load(Object source, EventArgs args) {
        Hashtable docIds = new Hashtable();
        SortedList terms = new SortedList();
        ArrayList dups = new ArrayList();
        SqlConnection conn = CdrClient.dbConnect("CdrGuest");
        try {
            SqlCommand cmd = new SqlCommand(@"
                    SELECT doc_id, value
                      FROM query_term
                     WHERE path = '/GlossaryTerm/TermName'
                  ORDER BY value", conn);
            cmd.CommandTimeout = 300;
            SqlDataReader reader = cmd.ExecuteReader();
            while (reader.Read()) {
                int docId = (int)reader[0];
                string name = (string)reader[1];
                string key = name.ToUpper().Trim();
                if (terms.Contains(key)) {
                    dups.Add(new DuplicateTerm(name, docId,
                                               (GlossaryTerm)terms[key]));
                    docIds[docId] = terms[key];
                }
                else {
                    GlossaryTerm term = new GlossaryTerm(name, docId);
                    terms[key] = term;
                    docIds[docId] = term;
                }
            }
            reader.Close();
            cmd = new SqlCommand(@"
                SELECT doc_id, value
                  FROM query_term
                 WHERE path = '/GlossaryTerm/TermDefinition/DefinitionText'
                   AND value LIKE '%Also called%'", conn);
            cmd.CommandTimeout = 300;
            reader = cmd.ExecuteReader();
            int maxOtherNames = 0;
            while (reader.Read()) {
                int docId = (int)reader[0];
                string def = (string)reader[1];
                GlossaryTerm term = (GlossaryTerm)docIds[docId];
                int n = term.extractOtherNames(def.Trim());
                if (maxOtherNames < n)
                    maxOtherNames = n;
            }
            reader.Close();
            foreach (DuplicateTerm term in dups)
                term.addRow(dupTable);
            for (int i = 0; i < maxOtherNames; ++i) {
                HtmlTableCell cell = new HtmlTableCell("th");
                cell.InnerText = "Also Called " + (i + 1).ToString();
                headers.Cells.Add(cell);
            }
            foreach (GlossaryTerm term in terms.GetValueList()) {
                if (!term.done) {
                    foreach (string name in term.otherNames) {
                        if (terms.Contains(name.ToUpper()))
                            ((GlossaryTerm)terms[name.ToUpper()]).done = true;
                    }
                    term.addRow(reportTable, maxOtherNames + 2);
                }
            }
        }
        finally {
            conn.Close();
        }
    }
</script>
<html>
 <head>
  <title>Glossary Term Concept Report</title>
  <style type='text/css'>
   body { font-family: Arial; }
   h1   { font-size: 14pt; }
   h2   { font-size: 12pt; }
   #dupTable td { color: red; }
  </style>
 </head>
 <body>
  <h1>Glossary Term Concept Report</h1>
  <h2>Duplicate Names</h2>
  <table id='dupTable' runat='server' border='1'
         cellpadding='3' cellspacing='0'>
   <tr>
    <th>CDR ID</th>
    <th>Glossary Term</th>
    <th>Duplicate Of</th>
    <th>Whose Name Is</th>
   </tr>
  </table>
  <br />
  <h2>Terms With Aliases</h2>
  <table id='reportTable' runat='server'
         border='1' cellpadding='3' cellspacing='0'>
   <tr id='headers'>
    <th>CDR ID</th>
    <th>Glossary Term</th>
   </tr>
  </table>
 </body>
</html>
