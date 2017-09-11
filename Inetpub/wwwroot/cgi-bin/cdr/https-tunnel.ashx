<%@ WebHandler Language="C#" Class="Handler" %>

/*
 * Passthrough to tunnel CDR client-server traffic through HTTPS instead
 * of running over custom port 2019.
 *
 * JIRA::OCECDR-3748
 */

public class Handler : System.Web.IHttpHandler {
    public void ProcessRequest(System.Web.HttpContext context) {

        // Read the bytes for the request.
        byte[] request = new byte[context.Request.InputStream.Length];
        context.Request.InputStream.Read(request, 0, request.Length);

        // Don't allow logon requests to bypass Windows authentication.
        if (has_logon(request)) {
            context.Response.Status = "403 Forbidden";
            context.Response.StatusCode = 403;
            return;
        }

        // Hand the request off to the CDR Server over our custom port.
        System.Net.Sockets.TcpClient sock = new System.Net.Sockets.TcpClient();
        sock.Connect("localhost", 2019);
        System.Net.Sockets.NetworkStream stream = sock.GetStream();
        int len = System.Net.IPAddress.HostToNetworkOrder(request.Length);
        byte[] len_bytes = System.BitConverter.GetBytes(len);
        stream.Write(len_bytes, 0, 4);
        stream.Write(request, 0, request.Length);

        // Fetch the response from the CDR Server.
        read(len_bytes, 4, stream);
        len = System.BitConverter.ToInt32(len_bytes, 0);
        len = System.Net.IPAddress.NetworkToHostOrder(len);
        byte[] response = new byte[len];
        read(response, len, stream);
        stream.Close();
        sock.Close();

        // Pass the response back to the ultimate CDR client.
        context.Response.ContentType = "application/xml";
        context.Response.Expires = -1;
        context.Response.BinaryWrite(response);
        log(request.Length, len);
    }

    // Fill up the caller's buffer with the response from the CDR server.
    static private void read(byte[] b, int n,
                             System.Net.Sockets.NetworkStream s) {
        int done = 0;
        while (done < n) {
            int bytes_read = s.Read(b, done, n - done);
            if (bytes_read > 0)
                done += bytes_read;
        }
    }

    // Each request get its own instance. Not much measurable effect on
    // performance (if anything, this approach is a teeny bit faster).
    public bool IsReusable { get { return false; } }

    // Record each request.
    private static void log(int request_length, int response_length) {
        string path = "d:\\cdr\\Log\\tunnel.log";
        System.IO.StreamWriter w =
            new System.IO.StreamWriter(path, true,
                                       System.Text.Encoding.UTF8);
        System.DateTime now = System.DateTime.Now;
        w.WriteLine("{0}: Request {1} bytes Response {2} bytes",
                    now.ToString("o"), request_length, response_length);
        w.Close();
    }

    // We can't allow outside requests to bypass the Windows authentication
    // implemented by IIS when obtaining CDR sessions. This takes about five
    // milliseconds for the average request. In an extreme case (for
    // example, a request of over 50MB, containing the string <CdrLogon
    // in a CDATA section, but not containing a CdrLogon element), the
    // test still takes under a second on the DEV server. Performance will
    // be even better in production, I expect.
    private static bool has_logon(byte[] bytes) {
        byte[] logon = System.Text.Encoding.ASCII.GetBytes("<CdrLogon");
        if (!contains(logon, bytes))
            return false;
        System.IO.MemoryStream stream = new System.IO.MemoryStream(bytes);
        System.Xml.XmlTextReader reader = new System.Xml.XmlTextReader(stream);
        while (reader.Read()) {
            if (reader.NodeType == System.Xml.XmlNodeType.Element)
                if (reader.Name == "CdrLogon")
                    return true;
        }
        return false;
    }

    // Determine whether a sequence of bytes contains another
    // specific sequence. Used as a first pass to see if '<CdrLogon'
    // appears in the request before parsing the XML to see if
    // the request really contains a CdrLogon element. Do it
    // this way to avoid the overhead of converting the bytes
    // to a String object.
    private static bool contains(byte[] needle, byte[] haystack) {
        for (int i = 0; i + needle.Length < haystack.Length; ++i) {
            bool found = true;
            for (int j = 0; j < needle.Length; ++j) {
                if (haystack[i + j] != needle[j]) {
                    found = false;
                    break;
                }
            }
            if (found)
                return true;
        }
        return false;
    }
}
