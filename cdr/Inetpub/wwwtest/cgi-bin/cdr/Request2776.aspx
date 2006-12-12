<%--
  =====================================================================
    $Id: Request2776.aspx,v 1.2 2006-12-12 14:49:45 bkline Exp $

    Report for Sheri on CTSU persons with no links from protocols.

    $Log: not supported by cvs2svn $
    Revision 1.1  2006/12/08 23:08:39  bkline
    New report for Sheri (see Bugzilla request #2776).

  =====================================================================
  --%>
<%@ Page Language='C#' %>
<%@ Import Namespace='System.Data' %>
<%@ Import Namespace='System.Data.SqlClient' %>

<script runat='server'>
    void Page_Load(Object source, EventArgs e) {
        string[] queries = new string[] {
            "CREATE TABLE #all_prots (id INT)",
            "CREATE TABLE #active_prots (id INT)",
            "CREATE TABLE #ctsu_persons (id INT)",
            "CREATE TABLE #persons_in_prots (id INT)",
            "CREATE TABLE #persons_in_active_prots (id INT)",
            @"INSERT INTO #all_prots
                   SELECT d.id
                     FROM document d
                     JOIN doc_type t
                       ON t.id = d.doc_type
                    WHERE t.name = 'InScopeProtocol'",
            @"INSERT INTO #active_prots
          SELECT DISTINCT doc_id
                    FROM query_term
                   WHERE path = '/InScopeProtocol/ProtocolAdminInfo'
                              + '/CurrentProtocolStatus'
                     AND value IN ('Active',
                                   'Approved-not yet active',
                                   'Temporarily closed')",
            @"INSERT INTO #ctsu_persons 
          SELECT DISTINCT m.doc_id
                     FROM external_map m
                     JOIN external_map_usage u
                       ON u.id = m.usage
                    WHERE u.name = 'CTSU_Person_ID'",
            @"INSERT INTO #persons_in_prots
          SELECT DISTINCT q.int_val
                     FROM query_term q
                     JOIN #all_prots a
                       ON a.id = q.doc_id
                     JOIN #ctsu_persons p
                       ON p.id = q.int_val",
            @"INSERT INTO #persons_in_active_prots
          SELECT DISTINCT q.int_val
                     FROM query_term q
                     JOIN #active_prots a
                       ON a.id = q.doc_id
                     JOIN #ctsu_persons p
                       ON p.id = q.int_val"
        };
        string[] tables = { "#persons_in_prots", "#persons_in_active_prots" };
        DataGrid[] dataGrids = { grid1, grid2 };
        SqlConnection conn = CdrClient.dbConnect("CdrGuest");
        try {
            foreach (string query in queries) {
                SqlCommand c = new SqlCommand(query, conn);
                c.CommandTimeout = 300;
                c.ExecuteNonQuery();
            }
            for (int i = 0; i < dataGrids.Length; ++i) {
                string query = String.Format(@"
                    SELECT d.id AS doc_id, d.title AS doc_title
                      FROM document d
                      JOIN #ctsu_persons p
                        ON p.id = d.id
                     WHERE d.id NOT IN (SELECT id FROM {0})
                  ORDER BY d.id", tables[i]);
                SqlCommand cmd = new SqlCommand(query, conn);
                cmd.CommandTimeout = 300;
                SqlDataAdapter da = new SqlDataAdapter(cmd);
                DataSet ds = new DataSet();
                da.Fill(ds);
                dataGrids[i].DataSource = ds;
                dataGrids[i].DataBind();
            }
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
   h1 { font-size: 14pt; }
  </style>
 </head>
 <body>
  <h1>CTSU Persons To Which No Protocols Link</h1>
  <asp:DataGrid id='grid1' runat='server' CellPadding='5'
                HeaderStyle-BackColor='PapayaWhip' BorderWidth='5px'
                BorderColor='#009' AlternatingItemStyle-BackColor='LightGrey'
                HeaderStyle-Font-Bold='True' AutoGenerateColumns='False'>
   <Columns>
    <asp:BoundColumn DataField='doc_id' HeaderText='CDR ID' />
    <asp:BoundColumn DataField='doc_title' HeaderText='Doc Title' />
   </Columns>
  </asp:DataGrid>
  <h1>CTSU Persons To Which No Active Protocols Link</h1>
  <asp:DataGrid id='grid2' runat='server' CellPadding='5'
                HeaderStyle-BackColor='PapayaWhip' BorderWidth='5px'
                BorderColor='#009' AlternatingItemStyle-BackColor='LightGrey'
                HeaderStyle-Font-Bold='True' AutoGenerateColumns='False'>
   <Columns>
    <asp:BoundColumn DataField='doc_id' HeaderText='CDR ID' />
    <asp:BoundColumn DataField='doc_title' HeaderText='Doc Title' />
   </Columns>
  </asp:DataGrid>
 </body>
</html>
