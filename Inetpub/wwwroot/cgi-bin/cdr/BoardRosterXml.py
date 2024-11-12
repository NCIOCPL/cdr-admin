#!/usr/bin/env python

"""Fetch board member information as a service.
"""

from cdrapi.docs import Doc
from cdrcgi import Controller
from lxml import etree


class Control(Controller):
    """Access to the database and the current CDR logon session."""

    CDR_REF = f"{{{Doc.NS}}}ref"
    CDR_ID = f"{{{Doc.NS}}}id"
    PERSON = "/PDQBoardMemberInfo/BoardMemberName/@cdr:ref"
    MEMBERSHIP_DETAILS = "/PDQBoardMemberInfo/BoardMembershipDetails"
    CURRENT = f"{MEMBERSHIP_DETAILS}/CurrentMember"
    BOARD = f"{MEMBERSHIP_DETAILS}/BoardName/@cdr:ref"
    BOARD_NAME = "/Organization/OrganizationNameInformation/OfficialName/Name"
    TERM_START_DATE = f"{MEMBERSHIP_DETAILS}/TermStartDate"
    EIC_START_DATE = f"{MEMBERSHIP_DETAILS}/EditorInChief/TermStartDate"
    EIC_END_DATE = f"{MEMBERSHIP_DETAILS}/EditorInChief/TermEndDate"
    FIELDS = (
        "m.doc_id AS member_id",
        "s.value AS eic_start",
        "f.value AS eic_finish",
        "t.value AS term_start",
        "d.title AS person_name",
        "m.int_val AS board_id",
    )

    def run(self):
        """Override the base class version, as this isn't a tabular report."""

        if self.member:
            node = self.member.node
        elif self.board:
            node = self.board.node
        else:
            node = self.node
        opts = dict(encoding="unicode", pretty_print=True)
        self.send_page(etree.tostring(node, **opts), text_type="xml")

    @property
    def board(self):
        """Specific board for which information is requested."""

        if not hasattr(self, "_board"):
            self._board = None
            id = self.fields.getvalue("board")
            if id:
                self._board = Board(self, id)
        return self._board

    @property
    def boards(self):
        """Board names indexed by Organization document ID."""

        if not hasattr(self, "_boards"):
            query = self.Query("query_term", "doc_id", "value")
            query.where(f"path = '{self.BOARD_NAME}'")
            query.where("value LIKE 'PDQ%Editorial%Board'")
            rows = query.execute(self.cursor).fetchall()
            self._boards = dict([tuple(row) for row in rows])
        return self._boards

    @property
    def member(self):
        """Specific member for which information is requested."""

        if not hasattr(self, "_member"):
            self._member = None
            id = self.fields.getvalue("member")
            if id:
                self._member = MemberDetails(self, id)
        return self._member

    @property
    def node(self):
        """Information on all boards/members."""

        if not hasattr(self, "_node"):
            query = self.Query("query_term m", *self.FIELDS)
            query.join("query_term c", "c.doc_id = m.doc_id",
                       "LEFT(c.node_loc, 4) = LEFT(m.node_loc, 4)")
            query.join("query_term p", "p.doc_id = m.doc_id")
            query.join("active_doc d", "d.id = p.doc_id")
            query.outer("query_term t", "t.doc_id = m.doc_id",
                        "LEFT(t.node_loc, 4) = LEFT(m.node_loc, 4)",
                        f"t.path = '{self.TERM_START_DATE}'")
            query.outer("query_term s", "s.doc_id = m.doc_id",
                        "LEFT(s.node_loc, 4) = LEFT(m.node_loc, 4)",
                        f"s.path = '{self.EIC_START_DATE}'")
            query.outer("query_term f", "f.doc_id = m.doc_id",
                        "LEFT(f.node_loc, 4) = LEFT(m.node_loc, 4)",
                        f"f.path = '{self.EIC_END_DATE}'")
            query.where(f"m.path = '{self.BOARD}'")
            query.where(f"c.path = '{self.CURRENT}'")
            query.where(f"p.path = '{self.PERSON}'")
            query.where("c.value = 'Yes'")
            self._node = etree.Element("BoardMembers")
            for row in query.execute(self.cursor).fetchall():
                self._node.append(BoardMember(self, row).node)
        return self._node


class Board:
    """PDQ Board, with information about its members."""

    def __init__(self, control, id):
        """Capture the caller's values.

        Pass:
            control - access to the database
            id - CDR ID of the board's Organization document
        """

        self.__control = control
        self.__id = id

    @property
    def id(self):
        """Integer for the CDR ID of the board's Organization document."""
        return Doc.extract_id(self.__id)

    @property
    def members(self):
        """Ordered sequence of MemberDetails objects."""

        if not hasattr(self, "_members"):
            fields = "b.doc_id", "a.title"
            query = self.__control.Query("query_term b", *fields).unique()
            query.join("query_term c", "c.doc_id = b.doc_id",
                       "LEFT(c.node_loc, 4) = LEFT(b.node_loc, 4)")
            query.join("active_doc a", "a.id = c.doc_id")
            query.where(f"b.path = '{Control.BOARD}'")
            query.where(f"c.path = '{Control.CURRENT}'")
            query.where("c.value = 'Yes'")
            query.where(query.Condition("b.int_val", self.id))
            query.order("a.title")
            self._members = []
            for row in query.execute(self.__control.cursor).fetchall():
                self._members.append(MemberDetails(self.__control, row.doc_id))
        return self._members

    @property
    def name(self):
        """String for the board's name."""

        if not hasattr(self, "_name"):
            doc = Doc(self.__control.session, id=self.id)
            self._name = doc.title.split(";")[0].strip()
        return self._name

    @property
    def node(self):
        """XML document to return with this board's detailed info."""

        if not hasattr(self, "_node"):
            self._node = etree.Element("Board")
            etree.SubElement(self._node, "BoardId").text = str(self.id)
            etree.SubElement(self._node, "BoardName").text = self.name
            for member in self.members:
                self._node.append(member.node)
        return self._node


class BoardMember:
    """Summary information about a board member for the complete roster."""

    def __init__(self, control, row):
        """Remember the caller's values.

        Pass:
            control - access to the database
            row - values from the database for this board member
        """

        self.__control = control
        self.__row = row

    @property
    def board_name(self):
        """String for the name of the board of which person is a member."""
        return self.__control.boards[self.__row.board_id]

    @property
    def id(self):
        """CDR ID for the PDQBoardMemberInfo document."""
        return self.__row.member_id

    @property
    def is_eic(self):
        """Boolean: is this member an editor-in-chief?"""

        now = str(self.__control.started)[:10]
        if not self.__row.eic_start or self.__row.eic_start > now:
            return False
        if self.__row.eic_finish and self.__row.eic_finish <= now:
            return False
        return True

    @property
    def name(self):
        """Name string extracted from the Person's document title."""

        if not hasattr(self, "_name"):
            name = self.__row.person_name.split(";")[0].strip()
            self._name = name.replace(" (board membership information)", "")
        return self._name

    @property
    def node(self):
        """Prepare the values for export through the service."""

        node = etree.Element("BoardMember")
        etree.SubElement(node, "DocId").text = str(self.id)
        etree.SubElement(node, "Name").text = self.name
        etree.SubElement(node, "IsEic").text = "Yes" if self.is_eic else "No"
        etree.SubElement(node, "TermStart").text = self.__row.term_start
        etree.SubElement(node, "BoardName").text = self.board_name
        etree.SubElement(node, "BoardId").text = str(self.__row.board_id)
        return node


class MemberDetails:
    """Detailed information about a single board member."""

    def __init__(self, control, id):
        """Save the caller's values.

        Pass:
            control - access to the database and the current CDR session
            id - CDR ID of the PDQBoardMemberInfo document
        """

        self.__control = control
        self.__id = id

    @property
    def contact(self):
        """Contact information for the board member."""

        if not hasattr(self, "_contact"):
            self._contact = self.Contact(self)
        return self._contact

    @property
    def control(self):
        """Access to the database and the current CDR session."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for the PDQBoardMemberInfo document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.__id)
        return self._doc

    @property
    def node(self):
        """XML document to return with this board member's detailed info."""

        if not hasattr(self, "_node"):
            self._node = etree.Element("BoardMember")
            etree.SubElement(self._node, "DocId").text = str(self.doc.id)
            etree.SubElement(self._node, "PersonId").text = str(self.person.id)
            self._node.append(self.person.node)
            self._node.append(self.contact.node)
            node = self.doc.root.find("GovernmentEmployee")
            etree.SubElement(self._node, "GovernmentEmployee").text = node.text
            if node.get("HonorariaDeclined"):
                etree.SubElement(self._node, "HonorariaDeclined").text = "Yes"
        return self._node

    @property
    def person(self):
        """Personal information about the board member."""

        if not hasattr(self, "_person"):
            node = self.doc.root.find("BoardMemberName")
            id = node.get(Control.CDR_REF)
            self._person = self.Person(self.control, id)
        return self._person

    class Contact:
        """Contact information for the board member."""

        PERSON_CONTACT_ID = "BoardMemberContact/PersonContactID"
        SPECIFIC_CONTACT = "BoardMemberContact/SpecificBoardMemberContact"
        SPECIFIC_EMAIL = f"{SPECIFIC_CONTACT}/BoardContactEmail"
        SPECIFIC_FAX = f"{SPECIFIC_CONTACT}/BoardContactFax"
        SPECIFIC_PHONE = f"{SPECIFIC_CONTACT}/BoardContactPhone"
        LOCATION_TAGS = {
            "Home",
            "OtherPracticeLocation",
            "PrivatePracticeLocation"
        }

        def __init__(self, member):
            """Save the caller's information.

            Pass:
                node - portion of the Person document with the contact info
            """

            self.__member = member

        @property
        def email(self):
            """Get the best email address we have."""

            if not hasattr(self, "_email"):
                self._email = None
                node = self.__member.doc.root.find(self.SPECIFIC_EMAIL)
                if node is not None:
                    self._email = self.Email(node)
                elif self.location:
                    self._email = self.location.email
            return self._email

        @property
        def fax(self):
            """Get the best fax number we can find."""

            if not hasattr(self, "_fax"):
                self._fax = None
                node = self.__member.doc.root.find(self.SPECIFIC_FAX)
                if node is not None:
                    self._fax = Doc.get_text(node, "").strip()
                elif self.location:
                    self._fax = self.location.fax
            return self._fax

        @property
        def location(self):
            """Location matching the value in the PersonContactID element."""

            if not hasattr(self, "_location"):
                self._location = None
                node = self.__member.doc.root.find(self.PERSON_CONTACT_ID)
                if node is None:
                    return None
                id = Doc.get_text(node, "").strip()
                if not id:
                    return None
                query = f'//*[@cdr:id="{id}"]'
                opts = dict(namespaces=Doc.NSMAP)
                for node in self.__member.person.doc.root.xpath(query, **opts):
                    if node.tag in self.LOCATION_TAGS:
                        if node.tag == "OtherPracticeLocation":
                            args = self.__member.control, node
                            self._location = self.OtherPracticeLocation(*args)
                        else:
                            self._location = self.Detail(node)
                        break
            return self._location

        @property
        def node(self):
            """Contact information packaged for return to the browser."""

            if not hasattr(self, "_node"):
                self._node = etree.Element("Contact")
                if self.phone:
                    self._node.append(self.phone.node)
                if self.fax:
                    etree.SubElement(self._node, "Fax").text = self.fax
                if self.email:
                    self._node.append(self.email.node)
            return self._node

        @property
        def phone(self):
            """Get the best phone number we can find."""

            if not hasattr(self, "_phone"):
                self._phone = None
                node = self.__member.doc.root.find(self.SPECIFIC_PHONE)
                if node is not None:
                    self._phone = self.Phone(node)
                elif self.location:
                    self._phone = self.location.phone
            return self._phone

        class Phone:
            """Phone number and indication whether the number is public."""

            def __init__(self, node):
                """Save the caller's information.

                Pass:
                    node - XML document node with the phone information
                """

                self.__node = node

            @property
            def node(self):
                """Phone information packaged for inclusion in the report."""

                public = "No" if self.__node.get("Public") == "No" else "Yes"
                node = etree.Element("Phone")
                number = Doc.get_text(self.__node, "").strip()
                etree.SubElement(node, "Number").text = number
                etree.SubElement(node, "Public").text = public
                return node

        class Email:
            """Email address and indication whether the address is public."""

            def __init__(self, node):
                """Save the caller's information.

                Pass:
                    node - XML document node with the email information
                """

                self.__node = node

            @property
            def node(self):
                """Email information packaged for inclusion in the report."""

                public = "No" if self.__node.get("Public") == "No" else "Yes"
                node = etree.Element("Email")
                address = Doc.get_text(self.__node, "").strip()
                etree.SubElement(node, "Address").text = address
                etree.SubElement(node, "Public").text = public
                return node

        class Detail:
            """Contact info for a location not associated with an org."""

            def __init__(self, node):
                """Save the caller's information.

                Pass:
                    node - portion of XML document with contact information
                """

                self.__node = node

            @property
            def email(self):
                """Email address for this location."""

                if not hasattr(self, "_email"):
                    self._email = None
                    node = self.__node.find("Email")
                    if node is not None:
                        self._email = MemberDetails.Contact.Email(node)
                return self._email

            @property
            def fax(self):
                """Fax number for this location."""
                return Doc.get_text(self.__node.find("Fax"), "").strip()

            @property
            def phone(self):
                """Toll-free phone if present, otherwise regular phone."""

                if not hasattr(self, "_phone"):
                    self._phone = None
                    node = self.__node.find("TollFreePhone")
                    if node is None:
                        node = self.__node.find("Phone")
                    if node is not None:
                        self._phone = MemberDetails.Contact.Phone(node)
                return self._phone

        class OtherPracticeLocation:
            """Location associated with an organization."""

            LOCATION_PATH = "OrganizationLocations/OrganizationLocation"

            def __init__(self, session, node):
                """Save the caller's values.

                Pass:
                    control - access to the current login session
                    node - node from an XML document with contact information
                """

                self.__control = control
                self.__node = node

            @property
            def email(self):
                """Pick a email address preferring specific over org."""

                if not hasattr(self, "_email"):
                    self._email = None
                    node = self.__node.find("SpecificEmail")
                    if node is not None:
                        self._email = MemberDetails.Contact.Email(node)
                    elif self.organization:
                        self._email = self.organization.email
                return self._email

            @property
            def fax(self):
                """Pick a fax number preferring specific over org."""

                if not hasattr(self, "_fax"):
                    self._fax = None
                    node = self.__node.find("SpecificFax")
                    if node is not None:
                        self._fax = Doc.get_text(node, "").strip()
                    elif self.organization:
                        self._fax = self.organization.fax
                return self._fax

            @property
            def organization(self):
                """Contact information for the location's organization."""

                if not hasattr(self, "_organization"):
                    self._organization = None
                    node = self.__node.find("OrganizationLocation")
                    org = None
                    if node is not None:
                        id = node.get(Control.CDR_REF, "").strip()
                        if "#" in id:
                            doc_id, frag_id = id.split("#", 1)
                            if frag_id:
                                org = Doc(self.__control.session, id=id)
                    if org is not None:
                        for node in org.root.findall(self.LOCATION_PATH):
                            if node.get(Control.CDR_ID) == frag_id:
                                child = node.find("Location")
                                if child is not None:
                                    Detail = MemberDetails.Contact.Detail
                                    self._organization = Detail(child)
                                break
                return self._organization

            @property
            def phone(self):
                """Pick a phone number preferring specific and toll-free."""

                if not hasattr(self, "_phone"):
                    self._phone = None
                    node = self.__node.find("SpecificTollFreePhone")
                    if node is None:
                        node = self.__node.find("SpecificPhone")
                    if node is not None:
                        self._phone = MemberDetails.Contact.Phone(node)
                    elif self.organization:
                        self._phone = self.organization.phone
                return self._phone

    class Person:
        """Information from the board member's Person document."""

        NAME_TAGS = (
            ("GivenName", "First"),
            ("MiddleInitial", "Middle"),
            ("SurName", "Last"),
            ("GenerationSuffix", "Gen"),
            ("NameFormat", "Format"),
        )
        SUFFIX_TAGS = "StandardProfessionalSuffix", "CustomProfessionalSuffix"

        def __init__(self, control, id):
            """Save the caller's information.

            Pass:
                control - access to the database and the current CDR session
                id - CDR ID of the PDQBoardMemberInfo document
            """

            self.__control = control
            self.__id = id

        @property
        def doc(self):
            """`Doc` object for the board member's Person document."""

            if not hasattr(self, "_doc"):
                self._doc = Doc(self.__control.session, id=self.__id)
            return self._doc

        @property
        def id(self):
            """CDR ID for the Person document."""
            return self.doc.id

        @property
        def node(self):
            """Personal name information block."""

            if not hasattr(self, "_node"):
                node = self.doc.root.find("PersonNameInformation")
                self._node = etree.Element("Name")
                for incoming, outgoing in self.NAME_TAGS:
                    value = Doc.get_text(node.find(incoming))
                    if value:
                        etree.SubElement(self._node, outgoing).text = value
                for child in node.findall("ProfessionalSuffix/*"):
                    if child.tag in self.SUFFIX_TAGS:
                        value = Doc.get_text(child)
                        if value:
                            etree.SubElement(self._node, "Suffix").text = value
            return self._node


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("Failure generating XML report")
        control.bail(e)
