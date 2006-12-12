<%--
  =====================================================================
    $Id: Request2776.aspx,v 1.4 2006-12-12 19:26:45 bkline Exp $

    Report for Sheri on CTSU persons with no links from protocols.

    $Log: not supported by cvs2svn $
    Revision 1.3  2006/12/12 19:25:26  bkline
    Completely rewritten (Sheri didn't really say what she wanted the first
    time).

    Revision 1.2  2006/12/12 14:49:45  bkline
    Syntax cleanup.

    Revision 1.1  2006/12/08 23:08:39  bkline
    New report for Sheri (see Bugzilla request #2776).

  =====================================================================
  --%>
<%@ Page Language='C#' Debug='True' %>
<%@ Import Namespace='System.Data' %>
<%@ Import Namespace='System.Data.SqlClient' %>

<script runat='server'>
    void Page_Load(Object source, EventArgs e) {

        // Measure performance.
        DateTime start = DateTime.Now;

        // Break the queries down into baby steps (hand optimization).
        string[] queries = new string[] {
            @"CREATE TABLE #idtype (p INT, loc VARCHAR(160))",
            @"CREATE TABLE #idval (p INT, id VARCHAR(800), loc VARCHAR(160))",
            @"CREATE TABLE #ctsu_prot_persons (prot INT, person VARCHAR(800))",
            @"CREATE TABLE #ctsu_persons (id NVARCHAR(356))",
            @"CREATE TABLE #active_protocols (id INT)",
            @"CREATE TABLE #persons_in_prots (id VARCHAR(800))",
            @"CREATE TABLE #persons_in_active_prots (id VARCHAR(800))",
            @"INSERT INTO #idtype
                   SELECT doc_id, node_loc
                     FROM query_term
                    WHERE path = '/InScopeProtocol/ProtocolAdminInfo'
                               + '/ExternalSites/ExternalSite'
                               + '/ExternalSitePI/ExternalID/@Type'
                      AND value = 'CTSU_person_id'",
            @"INSERT INTO #idval
                   SELECT doc_id, value, node_loc
                     FROM query_term
                    WHERE path = '/InScopeProtocol/ProtocolAdminInfo'
                               + '/ExternalSites/ExternalSite'
                               + '/ExternalSitePI/ExternalID'",
            @"INSERT INTO #ctsu_prot_persons
                   SELECT v.p, v.id
                     FROM #idval v
                     JOIN #idtype t
                       ON t.p = v.p
                      AND t.loc = v.loc",
            @"INSERT INTO #persons_in_prots
          SELECT DISTINCT person
                     FROM #ctsu_prot_persons",
            @"INSERT INTO #active_protocols
          SELECT DISTINCT doc_id
                     FROM query_term
                    WHERE path = '/InScopeProtocol/ProtocolAdminInfo'
                               + '/CurrentProtocolStatus'
                      AND value IN ('Active',
                                    'Approved-not yet active',
                                    'Temporarily closed')",
            @"INSERT INTO #persons_in_active_prots
          SELECT DISTINCT p.person
                     FROM #ctsu_prot_persons p
                     JOIN #active_protocols a
                       ON p.prot = a.id",
            @"INSERT INTO #ctsu_persons
          SELECT DISTINCT m.value
                     FROM external_map m
                     JOIN external_map_usage u
                       ON u.id = m.usage
                    WHERE u.name = 'CTSU_Person_ID'
                      AND m.doc_id IS NULL"
        };
        string[] tables = { "#persons_in_prots", "#persons_in_active_prots" };
        HtmlTable[] reportTables = { tbl1, tbl2 };
        SqlConnection conn = CdrClient.dbConnect("CdrGuest");
        try {
            foreach (string query in queries) {
                SqlCommand c = new SqlCommand(query, conn);
                c.CommandTimeout = 300;
                c.ExecuteNonQuery();
            }
            for (int i = 0; i < reportTables.Length; ++i) {
                string query = String.Format(@"
                    SELECT id
                      FROM #ctsu_persons
                     WHERE id NOT IN (SELECT id FROM {0})
                  ORDER BY id", tables[i]);
                SqlCommand cmd = new SqlCommand(query, conn);
                cmd.CommandTimeout = 300;
                SqlDataReader reader = cmd.ExecuteReader();
                while (reader.Read()) {
                    string id = (string)reader[0];
                    object[] values = { id };
                    CdrClient.addHtmlTableRow(reportTables[i], values);
                }
                reader.Close();
            }
            DateTime finish = DateTime.Now;
            TimeSpan delta = finish.Subtract(start);
            int ms = (int)delta.TotalMilliseconds;
            timing.InnerText = String.Format("Processing time: {0} ms.", ms);
        }
        finally {
            conn.Close();
        }
    }
</script>
<html>
 <head>
  <title>CTSU Persons Not Linked To By Protocols</title>
  <style type='text/css'>
   body { font-family: Arial; }
   h1 { font-size: 14pt; }
   #timing {font-size: 7pt; color: green; }
  </style>
 </head>
 <body>
  <h1>CTSU Persons To Which No Protocols Link</h1>
  <table id='tbl1' runat='server' border='1' cellpadding='3' cellspacing='0'>
   <tr>
    <th>CTSU ID</th>
   </tr>
  </table>
  <br />
  <h1>CTSU Persons To Which No Active Protocols Link</h1>
  <table id='tbl2' runat='server' border='1' cellpadding='3' cellspacing='0'>
   <tr>
    <th>CTSU ID</th>
   </tr>
  </table>
  <br />
  <span id='timing' runat='server' />
 </body>
</html>
