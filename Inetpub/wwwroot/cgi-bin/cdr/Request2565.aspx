<%--
  =====================================================================
    $Id$

    Second Glossary Term Report for Margaret (request #2565).

    $Log: not supported by cvs2svn $
    Revision 1.2  2007/01/23 22:11:35  bkline
    Sheri didn't like previous version; wants special handling for markup;
    changes to combinations of search elements (at her request).

    Revision 1.1  2006/12/18 01:53:50  bkline
    Report for Margaret to support preparation of GlossaryTerm documents
    for refactoring.

  =====================================================================
  --%>
<%@ Page Language='C#' EnableViewState='False' %>
<%@ Import Namespace='System.Data' %>
<%@ Import Namespace='System.Data.SqlClient' %>
<%@ Import Namespace='System.Xml' %>
<%@ Import Namespace='System.Text' %>
<script runat='server'>

    /**
     * <summary>
     *  Handler wired to the event fired when the control for the
     *  web page is loaded.  This is the top-level entry point
     *  for all of our processing work for the page.  We read
     *  the CGI form values and then if there is a user request
     *  we honor it, otherwise we put up the form used to select
     *  which glossary term documents to display in the report.
     *  If no documents are found matching the user's criteria,
     *  we put the form back up.  Note that we are careful to
     *  wrap the processing following the connection to the CDR
     *  database in a <code>try</code> block so we can ensure
     *  that the connection is closed even if an exception is
     *  thrown.  This version does not put up a custom error
     *  page for exceptions, as the report is not intended for
     *  use beyond the transition period to the new structure
     *  for glossary documents.
     * </summary>
     * <param name="source">Object sending the event (unused)</param>
     * <param name="args">Arguments passed to the handler (unused)</param>
     */
    void Page_Load(Object source, EventArgs args) {

        // Prepare local working variables.
        DateTime start    = DateTime.Now;
        string   title    = "CDR Administration";
        string   subtitle = "Glossary Term Concept and Definition Report";
        object[] commands = {
            "Submit Request",
            "Report Menu",
            "Admin Menu",
            "Log Out"
        };

        // Collect the CGI form values.
        string docId      = Request.Params.Get("docId");
        string searchTerm = Request.Params.Get("term");
        string termType   = Request.Params.Get("type");
        string termStatus = Request.Params.Get("status");
        string startDate  = Request.Params.Get("start");
        string endDate    = Request.Params.Get("end");
        string request    = Request.Params.Get("Request");
        string session    = Request.Params.Get("Session");
        
        // See if the user wants to go somewhere else.
        if (request == "Report Menu")
            Response.Redirect("Reports.py?Session=" + session);
        else if (request == "Admin Menu")
            Response.Redirect("Admin.py?Session=" + session);
        else if (request == "Log Out")
            Response.Redirect("Logout.py?Session=" + session);
                              
        // If we have criteria, perform a search.
        if (request == "Submit Request") {
            SqlConnection conn = Cdr.Client.dbConnect("CdrGuest");
            try {
                ArrayList docIds = null;
                if (docId.Length > 0)
                    docIds = lookupDocId(docId, conn);
                else if (searchTerm.Length > 0)
                    docIds = lookupDocTerm(searchTerm, conn);
                else if (termType.Length > 0)
                    docIds = lookupType(termType, conn);
                else if (termStatus.Length > 0)
                    docIds = lookupStatus(termStatus, startDate, endDate, 
                                          conn);
                if (docIds.Count == 0) {
                    warning.InnerText = "No terms match specified criteria";
                    showForm();
                }
                else {
                    showReport(docIds, conn);
                    commands[0] = "New Report";
                    Cdr.Client.showProcessingTime(start, timing);
                }
            }
            finally {
                conn.Close();
            }
        }
        else
            showForm();
        
        Cdr.Client.initWebAdminPage(banner, head, title, subtitle, commands);
    }

    /**
     * <summary>
     *  Object representing a single CDR GlossaryTerm document.
     *  There can be multiple instances of this class for each
     *  concept in the glossary, as the current document structure
     *  holds information for one of the names of the concept.
     *  This model will be changed so that there are two document
     *  types for glossary terms: one for the concepts and another
     *  for the names used to represent the concept (in fact,
     *  support for this shift is the role of this report).
     *  This is the base class, used for the alias terms used
     *  for a glossary concept.  The main term for the concept
     *  (the one which matches the user's search criteria)
     *  is represented by an object of the <see cref='GlossaryConcept'
     *  >GlossaryConcept</see> derived class.
     * </summary>
     */
    public class GlossaryTerm {

        // Instance-level data.
        protected int       docId;
        protected string    name;
        protected string    def;
        protected string    spDef;
        protected string    pron;

        /**
         * <summary>
         *  Base class default initializer.
         * </summary>
         */
        protected GlossaryTerm() {
            name  = null;
            docId = 0;
            def   = null;
            spDef = null;
            pron  = null;
        }
        
        /**
         * <summary>
         *  Used to create the objects for the concept's other names.
         * </summary>
         * <param name="name">Other name for the concept</param>
         * <param name="conn">Connection to the CDR database</param>
         */
        public GlossaryTerm(string name, SqlConnection conn) {
            this.name      = name;
            this.docId     = 0;
            this.def       = null;
            this.spDef     = null;
            this.pron      = null;
            SqlCommand cmd = new SqlCommand(@"
                SELECT doc_id
                  FROM query_term
                 WHERE path = '/GlossaryTerm/TermName'
                   AND value = @name", conn);
            cmd.Parameters.Add("@name", SqlDbType.NVarChar);
            cmd.Parameters[0].Value = name;
            SqlDataReader reader = cmd.ExecuteReader();
            while (reader.Read())
                this.docId = (int)reader[0];
            reader.Close();

            // Find the definitions and pronunciation for the term.
            if (this.docId != 0)
                init(conn);
        }

        /**
         * <summary>
         *  Provides read-only access to the name of the term (with
         *  pronunciation if present).
         * </summary>
         * <value>
         *  Name of the term, followed by the pronunciation in
         *  parentheses (if present).
         * </value>
         */
        public string Name {
            get {
                if (pron != null)
                    return String.Format("{0} ({1})", name, pron);
                return name;
            }
        }

        /**
         * <summary>
         *  Provides read-only access to the GlossaryTerm's CDR ID.
         * </summary>
         * <value>
         *  String value for CDR document ID of the term (or an
         *  empty string if we couldn't find the ID).
         * </value>
         */
        public string DocId {
            get {
                if (docId != 0)
                    return docId.ToString();
                return "";
            }
        }

        /**
         * <summary>
         *  Provides read-only access to the GlossaryTerm's definition.
         * </summary>
         * <value>
         *  Definition associated with this name for the concept;
         *  may contain "also called ..." segment at end, and may
         *  vary from the definitions tied to the other names for
         *  the concept.
         * </value>
         */
        public string Def { get { return def; }}

        /**
         * <summary>
         *  Provides read-only access to the GlossaryTerm's Spanish
         *  definition.
         * </summary>
         * <value>
         *  Spanish definition associated with this name for the
         *  concept.
         * </value>
         */
        public string SpDef { get { return spDef; }}

        /**
         * <summary>
         *  Common constructor code for the GlossaryTerm objects.
         *  Fills in the term's definition and pronunciation.
         * </summary>
         */
        private string parseDefinitionText(XmlElement e, SqlConnection conn) {
            string name = "DefinitionText";
            foreach (XmlNode child in e.GetElementsByTagName(name)) {
                return parseNodeContent(child);
            }
            return "";
        }
        protected void init(SqlConnection conn) {
            
            SqlCommand cmd = new SqlCommand(@"
                SELECT xml
                  FROM document
                 WHERE id = @docId", conn);
            cmd.Parameters.Add("@docId", SqlDbType.Int);
            cmd.Parameters[0].Value = docId;
            SqlDataReader reader = cmd.ExecuteReader();
            while (reader.Read()) {
                string docXml = (string)reader[0];
                XmlDocument doc = new XmlDocument();
                doc.LoadXml(docXml);
                XmlElement e = doc.DocumentElement;
                string name = "TermDefinition";
                StringBuilder sb = new StringBuilder();
                string br = "";
                foreach (XmlElement n in e.GetElementsByTagName(name)) {
                    sb.Append(br);
                    sb.Append(parseDefinitionText(n, conn));
                    br = "<br />";
                }
                this.def = sb.ToString();
                name = "SpanishTermDefinition";
                br = "";
                sb = new StringBuilder();
                foreach (XmlElement n in e.GetElementsByTagName(name)) {
                    sb.Append(br);
                    sb.Append(parseDefinitionText(n, conn));
                    br = "<br />";
                }
                this.spDef = sb.ToString();
                break;
            }
            reader.Close();
            string path = "/GlossaryTerm/TermPronunciation";
            foreach (string v in Cdr.Client.getQueryTermValuesForDoc(docId,
                                                                     path,
                                                                     conn)) {
                this.pron = v;
            }
        }
    }

    /**
     * <summary>
     *  The object for the first term associated with a concept carries
     *  a list of all of the other terms used for the concept.
     * </summary>
     */
    public class GlossaryConcept : GlossaryTerm {
        
        // Class-level data.
        private static string pattern = "(.+) (and|or) (.+)";
        private static Regex  regex = new Regex(pattern, 
                                                RegexOptions.Singleline);

        // Instance-level data.
        private ArrayList otherNames;

        /**
         * <summary>
         *  Used to create to first GlossaryTerm object for a concept.
         * </summary>
         * <param name="docId">CDR ID for the GlossaryTerm document</param>
         * <param name="conn">Connection to the CDR database</param>
         */
        public GlossaryConcept(int docId, SqlConnection conn) {
            this.docId  = docId;
            this.otherNames = new ArrayList();
            string path = "/GlossaryTerm/TermName";
            foreach (string v in Cdr.Client.getQueryTermValuesForDoc(docId,
                                                                     path,
                                                                     conn)) {
                this.name = v;
            }

            // Find the definition and pronunciation for the term.
            init(conn);

            // Find the other terms that are used for this concept.
            extractOtherNames(conn);
        }

        /**
         * <summary>
         *  Provides read-only access to the concept's other term names.
         * </summary>
         * <value>
         *  List of <see cref="GlossaryTerm">GlossaryTerm</see> objects
         *  for the other term names used to identify this concept.
         * </value>
         */
        public ArrayList OtherNames { get { return otherNames; }}

        /**
         * <summary>
         *  Parses out the other names used for this concept and
         *  builds a list of the GlossaryTerm objects corresponding
         *  to those names.
         * </summary>
         * <param name="conn">Connection to the CDR database</param>
         */
        private void extractOtherNames(SqlConnection conn) {

            string path = "/GlossaryTerm/TermDefinition/DefinitionText";
            string qtdef = "";
            foreach (string v in Cdr.Client.getQueryTermValuesForDoc(docId,
                                                                     path,
                                                                     conn)) {
                qtdef = v;
                break;
            }
            
            // Normalize white space.
            string d = qtdef.Replace("\n\r", " ").Replace("\n", " ")
                            .Replace("\r", " ").TrimEnd(".".ToCharArray());

            // Find the portion of the definition with term aliases.
            string ucDef = d.ToUpper();
            string label = "ALSO CALLED";
            int pos = ucDef.IndexOf(label);
            if (pos == -1)
                return;
            string alsoCalled = d.Substring(pos + label.Length);

            // Look for ..., ..., and ... pattern.
            Match match = GlossaryConcept.regex.Match(alsoCalled);
            if (match.Success) {

                // Split the parts before and after "and".
                string before = match.Groups[1].ToString();
                string after  = match.Groups[3].ToString();

                // Break the first part into tokens separated by ", ".
                int index = before.IndexOf(", ");
                while (index > -1) {
                    addOtherName(before.Substring(0, index), conn);
                    before = before.Substring(index + 2);
                    index = before.IndexOf(", ");
                }

                // Fold in the last two names.
                addOtherName(before, conn);
                addOtherName(after, conn);
            }

            else {

                // Only one alias: store it.
                addOtherName(alsoCalled, conn);
            }
        }

        /**
         * <summary>
         *  Helper method to strip off extraneous text around the
         *  term's name, construct a new GlossaryTerm object for it,
         *  and add it to our list of other names for the concept.
         * </summary>
         * <param name="termString">term name for the concept</param>
         * <param name="conn">Connection to the CDR database</param>
         */
        private void addOtherName(string termString, SqlConnection conn) {
            string s = termString.Trim();
            s = s.TrimEnd(",".ToCharArray());
            string ucString = s.ToUpper();
            if (ucString.StartsWith("A "))
                s = s.Substring(2).Trim();
            else if (ucString.StartsWith("AN "))
                s = s.Substring(3).Trim();
            else if (ucString.StartsWith("THE "))
                s = s.Substring(4).Trim();
            s = s.Trim();
            s = s.TrimEnd(".".ToCharArray());
            if (s.Length > 0) {
                otherNames.Add(new GlossaryTerm(s, conn));
            }
        }
    }

    /**
     * <summary>
     *  Puts up the CGI form in which the user specifies criteria
     *  for selection glossary concepts for the report.
     * </summary>
     */
    private void showForm() {
        string instructions = @"
            Specify CDR document ID, term substring, term type, or term 
            status,  When specifying term status you can optionally
            limit by date range for term status date.  Press Submit
            Request to generate report.";
        Cdr.Client.addCgiFormInstructions(formTable, instructions);
        Cdr.Client.addCgiTextField(formTable, "docId", "CDR ID:", "", "");
        Cdr.Client.addCgiTextField(formTable, "term", "Term Name:", "", "");
        Cdr.DocType dt = new Cdr.DocType("GlossaryTerm");
        string[] termTypes = dt.ValidValueLists["TermType"].Values;
        string[] termStatuses = dt.ValidValueLists["TermStatus"].Values;
        Cdr.Client.addCgiPicklist(formTable, "type", "Term Type:",
                                  termTypes, termTypes, "",
                                  "Optionally Select Term Type");
        Cdr.Client.addCgiPicklist(formTable, "status", "Term Status:",
                                  termStatuses, termStatuses, "",
                                  "Optionally Select Term Status");
        Cdr.Client.addCgiTextField(formTable, "start", "Start Date:", "",
                                   "CdrDateField");
        Cdr.Client.addCgiTextField(formTable, "end", "End Date:", "",
                                   "CdrDateField");
    }

    /**
     * <summary>
     *  Common code for extracting the list of document IDs; used
     *  by all of the different selection methods available to the
     *  user.
     * </summary>
     * <param name='cmd'>SQL query prepared for execution</param>
     * <returns>List of CDR document IDs</returns>
     */
    private ArrayList extractQueryResults(SqlCommand cmd) {
        cmd.CommandTimeout = 300;
        SqlDataReader reader = cmd.ExecuteReader();
        ArrayList arrayList = new ArrayList();
        while (reader.Read())
            arrayList.Add(reader[0]);
        reader.Close();
        return arrayList;
    }

    /**
     * <summary>
     *  Finds the Glossary Term document for the CDR ID entered by
     *  the user; returns an empty list if the term does not
     *  contain a definition with an "Also called ..." substring.
     * </summary>
     * <param name="idString">CDR ID for document</param>
     * <param name="conn">Connection to the CDR database</param>
     * <returns>List of CDR document IDs</returns>
     */
    private ArrayList lookupDocId(string idString, SqlConnection conn) {
        Cdr.DocID docId = new Cdr.DocID(idString);
        SqlCommand cmd = new SqlCommand(@"
                SELECT doc_id
                  FROM query_term
                 WHERE doc_id = @docId
                   AND path = '/GlossaryTerm/TermDefinition/DefinitionText'
                   AND value LIKE '%Also called%'", conn);
        cmd.Parameters.Add("@docId", SqlDbType.Int);
        cmd.Parameters[0].Value = docId.BaseID;
        return extractQueryResults(cmd);
    }

    /**
     * <summary>
     *  Finds the glossary terms with names containing the string
     *  entered by the user, and which have a definition containing
     *  the substring "Also Called".
     * </summary>
     * <param name="termString">User's search term</param>
     * <param name="conn">Connection to the CDR database</param>
     * <returns>List of CDR document IDs</returns>
     */
    private ArrayList lookupDocTerm(string termString, SqlConnection conn) {
        if (termString.IndexOf('%') == -1)
            termString = "%" + termString + "%";
        SqlCommand cmd = new SqlCommand(@"
            SELECT DISTINCT n.doc_id
                       FROM query_term n
                       JOIN query_term d
                         ON d.doc_id = n.doc_id
                      WHERE n.path = '/GlossaryTerm/TermName'
                        AND d.path = '/GlossaryTerm/TermDefinition'
                                   + '/DefinitionText'
                        AND n.value LIKE @termString
                        AND d.value LIKE '%Also called%'", conn);
        cmd.Parameters.Add("@termString", SqlDbType.NVarChar);
        cmd.Parameters[0].Value = termString;
        return extractQueryResults(cmd);
    }

    /**
     * <summary>
     *  Finds the glossary terms with status and/or type values
     *  entered by the user, and which have a definition containing
     *  the substring "Also Called".  User can specify term type,
     *  term status, or both.  If both are specified, only terms
     *  matching both criteria are returned.
     * </summary>
     * <param name="type">
     *  User-selected type value (if any); otherwise an empty string.
     * </param>
     * <param name="status">
     *  User-selected status value (if any); otherwise an empty string.
     * </param>
     * <param name="conn">Connection to the CDR database</param>
     * <returns>List of CDR document IDs</returns>
     */
    private ArrayList lookupType(string type, SqlConnection conn) {
        string query = String.Format(@"
            SELECT DISTINCT t.doc_id
                       FROM query_term t
                       JOIN query_term d
                         ON d.doc_id = t.doc_id
                      WHERE t.path = '/GlossaryTerm/TermType'
                        AND d.path = '/GlossaryTerm/TermDefinition'
                                   + '/DefinitionText'
                        AND d.value LIKE '%Also called%'
                        AND t.value = '{0}'", type);
        SqlCommand cmd = new SqlCommand(query, conn);
        return extractQueryResults(cmd);
    }

    /**
     * <summary>
     *  Finds the glossary term documents whose status date falls
     *  within the range entered by the user, and which have a
     *  definition containing the substring "Also Called".  Both
     *  starting and ending dates for the range will have been
     *  specified.
     * </summary>
     * <param name="start">Starting date for the range</param>
     * <param name="end">Ending date for the range</param>
     * <param name="conn">Connection to the CDR database</param>
     * <returns>List of CDR document IDs</returns>
     */
    private ArrayList lookupStatus(string status,
                                   string start, string end,
                                   SqlConnection conn) {
        if (start == null || start.Length == 0)
            start = "2002-01-01";
        if (end == null || end.Length == 0)
            end = "9999-01-01";
        SqlCommand cmd = new SqlCommand(@"
                SELECT DISTINCT d.doc_id
                  FROM query_term d
                  JOIN query_term sd
                    ON sd.doc_id = d.doc_id
                  JOIN query_term s
                    ON s.doc_id = d.doc_id
                 WHERE d.path = '/GlossaryTerm/TermDefinition/DefinitionText'
                   AND sd.path = '/GlossaryTerm/StatusDate'
                   AND s.path = '/GlossaryTerm/TermStatus'
                   AND s.value = @status
                   AND d.value LIKE '%Also called%'
                   AND sd.value BETWEEN @start AND
                                DATEADD(s, -1, DATEADD(d, 1, @end))",
                                        conn);
        cmd.Parameters.Add("@status", SqlDbType.NVarChar);
        cmd.Parameters.Add("@start", SqlDbType.DateTime);
        cmd.Parameters.Add("@end", SqlDbType.DateTime);
        cmd.Parameters[0].Value = status;
        cmd.Parameters[1].Value = start;
        cmd.Parameters[2].Value = end;
        return extractQueryResults(cmd);
    }

    private static HtmlTableRow addHtmlTableRow(HtmlTable table,
                                                object[] values) {
        HtmlTableRow row = new HtmlTableRow();
        table.Rows.Add(row);
        foreach (object value in values) { 
            HtmlTableCell cell = new HtmlTableCell();
            string text = "";
            if (value != null)
                text = value.ToString().Trim();
            if (text.Length == 0)
                text = "\u00A0";
            cell.InnerHtml = text;
            row.Cells.Add(cell);
        }
        return row;
    }

    /**
     * <summary>
     *  Populates the <code>report</code> control for the page.
     * </summary>
     * <param name="docIds">CDR document IDs for the report</param>
     * <param name="conn">Connection to the CDR database</param>
     * <returns>List of CDR document IDs</returns>
     */
    private void showReport(ArrayList docIds, SqlConnection conn) {

        // Suppress display of the CGI form.
        formTable.Style["display"] = "none";

        // Create a caption row for the report.
        HtmlGenericControl caption = new HtmlGenericControl("h1");
        report.Controls.Add(caption);
        caption.InnerText = "Glossary Term Names and Definitions ("
                          + docIds.Count.ToString()
                          + " Concept"
                          + ((docIds.Count == 1) ? "" : "s")
                          + " Found)";

        // Create the report table, and add it to the report block.
        HtmlTable table = new HtmlTable();
        table.CellSpacing = 0;
        table.CellPadding = 3;
        table.Border = 1;
        report.Controls.Add(table);

        // Add headers for the report's columns.
        HtmlTableRow row = new HtmlTableRow();
        table.Rows.Add(row);
        string[] hdrs = { "CDR ID", "Glossary Term (pronun)", "Definition",
                          "Spanish Definition",
                          "CDR ID", "Also Called (pronun)", "Definition" };
        foreach (string hdr in hdrs) {
            HtmlTableCell th = new HtmlTableCell("th");
            th.InnerText = hdr;
            row.Cells.Add(th);
        }

        // Create a list of objects for the concept matching the CDR IDs.
        SortedList terms = new SortedList();
        foreach (int docId in docIds) {
            GlossaryConcept term = new GlossaryConcept(docId, conn);
            terms[term.Name] = term;
        }

        // Populate the data rows for the report table.
        foreach (GlossaryConcept c in terms.Values) {
            bool first = true;
            object[] vals = null;

            foreach (GlossaryTerm o in c.OtherNames) {
                if (first) {
                    string cName = Cdr.Client.escapeXml(c.Name);
                    string oName = Cdr.Client.escapeXml(o.Name);
                    vals = new object[] { c.DocId, cName, c.Def, c.SpDef,
                                          o.DocId, oName, o.Def };
                    first = false;
                }
                else {
                    string oName = Cdr.Client.escapeXml(o.Name);
                    vals = new object[] { "", "", "", "",
                                          o.DocId, oName, o.Def, };
                }
                HtmlTableRow r = addHtmlTableRow(table, vals);
                alignCells(r);
            }
            if (first) {
                string cName = Cdr.Client.escapeXml(c.Name);
                vals = new object[] { c.DocId, cName, c.Def, c.SpDef,
                                      "", "", "" };
                HtmlTableRow r = addHtmlTableRow(table, vals);
                alignCells(r);
            }
        }
    }

    /**
     * Recursively extract the complete content of an element, tags and all.
     */
    private static string parseNodeContent(XmlNode node) {
        StringBuilder sb = new StringBuilder();
        parseNodeContent(node, sb);
        return sb.ToString();
    }
    private static void parseNodeContent(XmlNode node, StringBuilder sb) {
        string strikeout = "<span style='text-decoration: line-through'>";
        string red       = "<span style='color: red'>";
        foreach (XmlNode child in node.ChildNodes) {
        /*
            switch (child.NodeType) {
            case XmlNodeType.Text:
                sb.Append(Cdr.Client.escapeXml(child.Value));
                break;
            case XmlNodeType.CDATA:
                sb.Append(Cdr.Client.escapeXml(child.Value));
                break;
            case XmlNodeType.Element:
        */
        if (child.NodeType == XmlNodeType.Text || child.NodeType == XmlNodeType.CDATA)
            sb.Append(Cdr.Client.escapeXml(child.Value));
        else if (child.NodeType == XmlNodeType.Element) {
                switch (child.LocalName) {
                case "Insertion":
                    sb.Append(red);
                    parseNodeContent(child, sb);
                    sb.Append("</span>");
                    break;
                case "Deletion":
                    sb.Append(strikeout);
                    parseNodeContent(child, sb);
                    sb.Append("</span>");
                    break;
                case "Strong":
                    sb.Append("<b>");
                    parseNodeContent(child, sb);
                    sb.Append("</b>");
                    break;
                case "Emphasis":
                case "ScientificName":
                    sb.Append("<i>");
                    parseNodeContent(child, sb);
                    sb.Append("</i>");
                    break;
                default:
                    parseNodeContent(child, sb);
                    break;
                }
            }
        }
    }

    /**
     * <summary>
     *  Helper method to align text in the report cells to the
     *  upper left corner.
     * </summary>
     * <param name="row">
     *  Reference to row in which cells are to be aligned.
     * </param>
     */
    private void alignCells(HtmlTableRow row) {
        foreach (HtmlTableCell cell in row.Cells) {
            cell.Align = "left";
            cell.VAlign = "top";
        }
    }

</script>

<html>
 <head id='head' runat='server' />
 <script language='JavaScript' src='/js/CdrCalendar.js'></script>
 <script language='JavaScript'>
  <!--
   CdrCalendar.setReadOnly = false;
  // -->
 </script>
 <body>
  <form runat='server' method='post' action='/cgi-bin/cdr/DumpParams.py'>
   <div id='banner' runat='server' />
   <table id='formTable' runat='server' />
  </form>
  <div id='report' runat='server' />
  <div id='warning' runat='server' />
  <div id='timing' runat='server' />
 </body>
</html>
