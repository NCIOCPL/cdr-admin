print u"""\
Content-type: text/xml; charset=utf-8

<items>
 <item id="1" name="No\xebl">
  <address street="405 S. Barton St." city="Arlington" state="VA"/>
 </item>
 <item id="2" name="Fritz">
  <address street="123 Main St." city="Kalamazoo" state="MI"/>
  <address street="23 Skidoo" city="West Lansing" state="MI"/>
 </item>
</items>""".encode("utf-8")
 
