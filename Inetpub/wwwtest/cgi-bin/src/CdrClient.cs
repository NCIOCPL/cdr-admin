/*
 * $Id: CdrClient.cs,v 1.1 2006-12-12 15:41:46 bkline Exp $
 *
 * Client interface module for CDR.
 *
 * $Log: not supported by cvs2svn $
 */

using System;
using System.Data.SqlClient;

public class CdrClient {

    public static SqlConnection dbConnect(string uid) {
        string pwd = "***REMOVED***";
        switch (uid) {
            case "CdrGuest":
                pwd = "***REDACTED***";
                break;
            case "CdrPublishing":
                pwd = "***REMOVED***";
                break;
            case "cdr":
                break;
            default:
                string err = "unrecognized account: " + uid;
                throw new ApplicationException(err);
        }
        string dsn = String.Format("Database=cdr;User ID={0};" +
                                   "Password={1};" +
                                   "Server=localhost", uid, pwd);
        SqlConnection conn = new SqlConnection(dsn);
        conn.Open();
        return conn;
    }
    static void Main(string[] args) {
        SqlConnection conn = CdrClient.dbConnect("cdr");
        SqlCommand cmd = new SqlCommand(@"
            SELECT id, name
              FROM doc_type
          ORDER BY id", conn);
        SqlDataReader reader = cmd.ExecuteReader();
        while (reader.Read()) {
            int    id   = (int)reader[0];
            string name = (string)reader[1];
            Console.WriteLine("{0}\t{1}", id, name);
        }
        reader.Close();
    }
}
