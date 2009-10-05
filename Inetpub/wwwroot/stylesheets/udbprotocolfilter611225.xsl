<CdrDoc Type='Filter' Id='CDR0000190755'>
<CdrDocCtl>
<DocValStatus readonly="yes">U</DocValStatus>
<DocValDate readonly="yes">1900-01-01T00:00:00.000</DocValDate>
<DocTitle>Protocol Filter</DocTitle></CdrDocCtl>
<CdrDocXml><![CDATA[<?xml version="1.0"?>
<xsl:transform xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                version="1.0"
               xmlns:cdr="cips.nci.nih.gov/cdr">
  <xsl:output method="xml" omit-xml-declaration="no"/>
<!--Filter to create subset of CDR Protocol XML data for UDB-->
<!-- Elements copied are limited to elements available in current
     test data. Program will be updated when new test data is 
     available. Decisions are still in progress regarding data
     elements to be copied for UDB version of Protocol XML.
     Current file has elements that may be omitted later-->
<!-- Written by Cheryl Burg  5-31-2001 -->
<!-- Select data elements to be copied and add tags when an incomplete
     node is copied -->
  <xsl:template match="InScopeProtocol">
  <xsl:copy>
<!--Copy Protocol Identifiers  -->
<IdentificationInfo><ProtocolIDs><PrimaryID><xsl:apply-templates select="/InScopeProtocol/IdentificationInfo/ProtocolIDs/PrimaryID/IDstring" mode="copy"/></PrimaryID>
<OtherID><xsl:apply-templates select="/InScopeProtocol/IdentificationInfo/ProtocolIDs/OtherID/IDType" mode="copy"/>
<xsl:apply-templates select="/InScopeProtocol/IdentificationInfo/ProtocolIDs/OtherID/IDString" mode="copy"/></OtherID></ProtocolIDs></IdentificationInfo>
<!-- copy sponsor names -->
<SponsorName><xsl:apply-templates select="/InScopeProtocol/ProtocolSponsors/SponsorName" mode="copy"/></SponsorName>
<!-- Copy titles -->
<xsl:apply-templates select="/InScopeProtocol/ProtocolTitle" mode="copy"/>
<!-- Copy protocol abstract -->
<xsl:apply-templates select="/InScopeProtocol/ProtocolAbstract" mode="copy"/>
<!--code below can be used to select specific elements for Protocol Abstract
    XML node -->
<!--<Outline><Para><xsl:apply-templates select="/InScopeProtocol/ProtocolAbstract/Professional/Outline/Para" mode="copy"/></Para></Outline>
<EntryCriteria><Para><xsl:apply-templates select="/InScopeProtocol/ProtocolAbstract/Professional/EntryCriteria/Para" mode="copy"/></Para></EntryCriteria></Professional>
<Patient><Rationale><Para><xsl:apply-templates select="/InScopeProtocol/ProtocolAbstract/Patient/Rationale/Para" mode="copy"/></Para></Rationale>
<Purpose><Para><xsl:apply-templates select="/InScopeProtocol/ProtocolAbstract/Patient/Purpose/Para" mode="copy"/></Para></Purpose>
<TreatmentIntervention><Para><xsl:apply-templates select="/InScopeProtocol/ProtocolAbstract/Patient/TreatmentIntervention/Para" mode="copy"/></Para></TreatmentIntervention>
<EligibilityText><Para><xsl:apply-templates select="/InScopeProtocol/ProtocolAbstract/Patient/EligibilityText/Para" mode="copy"/></Para></EligibilityText></Patient></ProtocolAbstract>-->
<!--Copy Protocol Details, Eligibility, Phase, and Design -->
<xsl:apply-templates select="/InScopeProtocol/ProtocolDetails" mode="copy"/>
<xsl:apply-templates select="/InScopeProtocol/Eligibility" mode="copy"/>
<xsl:apply-templates select="/InScopeProtocol/ProtocolPhase" mode="copy"/>
<xsl:apply-templates select="/InScopeProtocol/ProtocolDesign" mode="copy"/>
<!-- Copy Protocol Special Category element -->
<ProtocolSpecialCategory><xsl:apply-templates select="/InScopeProtocol/ProtocolSpecialCategory/SpecialCategory" mode="copy"/></ProtocolSpecialCategory>
<!-- Copy Protocol Administrative Info including Organization and Participant
      Information -->
<ProtocolAdminInfo><CurrentProtocolStatus><xsl:apply-templates select="/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus/ProtocolStatusName" mode="copy"/></CurrentProtocolStatus>

<ProtocolLeadOrg><xsl:apply-templates select="/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/OrganizationID" mode="copy"/>

<xsl:apply-templates select="/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/OrgRole" mode="copy"/>

<xsl:apply-templates select="/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/UpdateGroup" mode="copy"/>

<xsl:apply-templates select="/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/OrgStatus" mode="copy"/>

<xsl:apply-templates select="/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/ProtocolIDString" mode="copy"/>

<ProtocolPersonnel><xsl:apply-templates select="/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/ProtocolPersonnel/PersonID" mode="copy"/>
<!-- link to Person XML record using CDR Unique ID to include additional
     identifying data elements -->
<xsl:for-each select="/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/ProtocolPersonnel">
 <xsl:choose>
 <xsl:when test="contains(PersonID/@cdr:ref,'CDR')">
 <xsl:variable name="PerId" select="PersonID/@cdr:ref"/>
 <xsl:variable name="PerInfo" select="document(concat('cdr:',$PerId))"/>
 <xsl:apply-templates select="$PerInfo/Person/PersonSurname" mode="copy"/>
 <xsl:apply-templates select="$PerInfo/Person/PersonGivenName" mode="copy"/>
 <xsl:apply-templates select="$PerInfo/Person/PersonInitials" mode="copy"/>
 <xsl:apply-templates select="$PerInfo/Person/PersonStat/PersonProfessionalSuffix" mode="copy"/>
</xsl:when>
<xsl:otherwise>
   Error, missing data
</xsl:otherwise>
</xsl:choose>
</xsl:for-each>
<xsl:apply-templates
select="/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/ProtocolPersonnel/PersonRole" mode="copy"/></ProtocolPersonnel></ProtocolLeadOrg>

<ProtocolSites><xsl:for-each select="/InScopeProtocol/ProtocolAdminInfo/ProtocolSites/Organization">
<Organization><xsl:apply-templates select="OrgID" mode="copy"/>

<xsl:apply-templates select="OrganizationStatus" mode="copy"/>
<OrganizationContact><SpecificPerson>

<xsl:apply-templates select="OrganizationContact/SpecificPerson/Person" mode="copy"/>

<xsl:apply-templates select="OrganizationContact/SpecificPerson/Role"
mode="copy"/>

<xsl:apply-templates select="OrganizationContact/SpecificPerson/SpecificPhone" mode="copy"/></SpecificPerson></OrganizationContact></Organization>

<!-- Link to Person XML records for Principal investigators to add
     additional data elements -->
 <xsl:choose>
 <xsl:when test="contains(OrganizationContact/SpecificPerson/Person/@cdr:ref,'CDR')">
 <xsl:variable name="PerId" select="OrganizationContact/SpecificPerson/Person/@cdr:ref"/>
 <xsl:variable name="PerInfo" select="document(concat('cdr:',$PerId))"/>
 <xsl:apply-templates select="$PerInfo/Person/PersonSurname" mode="copy"/>
 <xsl:apply-templates select="$PerInfo/Person/PersonGivenName" mode="copy"/>
 <xsl:apply-templates select="$PerInfo/Person/PersonInitials" mode="copy"/>
 <xsl:apply-templates select="$PerInfo/Person/PersonStat/PersonProfessionalSuffix" mode="copy"/>
</xsl:when>
<xsl:otherwise>
   Error, missing data
</xsl:otherwise>
</xsl:choose>
<!--code below can be uncommented and run if no output is available
     to determine if the record has no data for an element -->
<!-- <xsl:variable name="surname" select="$PerInfo/Person/PersonSurname"/>
<xsl:choose>
<xsl:when test="$surname"
</xsl:when>
<xsl:otherwise>
<xsl:text>Person Surname not available</xsl:text>
</xsl:otherwise>
</xsl:choose> -->
</xsl:for-each></ProtocolSites></ProtocolAdminInfo>
</xsl:copy>   
</xsl:template>

   <xsl:template match="@*|node()" mode="copy">
     <xsl:copy>
       <xsl:apply-templates select="@*" mode="copy"/>
       <xsl:apply-templates mode="copy"/>
     </xsl:copy> 
   </xsl:template>  
</xsl:transform>]]>
</CdrDocXml>
</CdrDoc>