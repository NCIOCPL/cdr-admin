// CogDemo.cs
public class CogDemoPage : System.Web.UI.Page {
   protected void Page_Load(object sender, System.EventArgs e) {
       if (IsPostBack)
           sendZipfile();
   }
   private void sendZipfile() {
       string               name   = "cog-protocols-20050524.zip";
       string               header = "attachment; filename=" + name;
       string               path   = "d:\\tmp\\" + name;
       System.IO.FileMode   mode   = System.IO.FileMode.Open;
       System.IO.FileStream fs     = new System.IO.FileStream(path, mode);
       byte[]               bytes  = new byte[fs.Length];
       fs.Read(bytes, 0, (int)fs.Length);
       fs.Close();
       Response.ContentType = "application/zip";
       Response.AddHeader("Content-Disposition", header);
       Response.BinaryWrite(bytes);
       Response.End();
   }
}
