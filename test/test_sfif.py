from sfif import correct_email
from acu_sf_sh_sys_data import EXT_REFS_SEP


class TestSfInterface:
    sf_id_of_rci_id = dict()

    def test_correct_email1(self):
        r = list()
        assert correct_email('abc."def".xyz@example.com', False, r) == ('abc."def".xyz@example.com', False)
        assert r == []
        assert correct_email('"abc"@example.com', False, r) == ('"abc"@example.com', False)
        assert r == []

        assert correct_email('abc"def"xyz@example.com', False, r) == ('abcdefxyz@example.com', True)
        assert r == ['3:"', '7:"']

        r = list()
        assert correct_email("john.smith(comment)@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["10:(comment)"]
        r = list()
        assert correct_email("(comment)john.smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["0:(comment)"]

        r = list()
        assert correct_email(".john.smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["0:."]
        r = list()
        assert correct_email("john.smith.@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["10:."]
        r = list()
        assert correct_email("john..smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["5:."]
        r = list()
        assert correct_email('"john..smith"@example.com', False, r) == ('"john..smith"@example.com', False)
        assert r == []

        # special characters !#$%&'*+-/=?^_`{|}~; are allowed in local part
        r = list()
        assert correct_email('john_smith@example.com', False, r) == ('john_smith@example.com', False)
        assert r == []
        r = list()
        assert correct_email('john?smith@example.com', False, r) == ('john?smith@example.com', False)
        assert r == []

        # space and "(),:;<>@[\] characters are allowed with restrictions (they are only allowed inside a quoted string,
        # as described in the paragraph below, and in addition, a backslash or double-quote must be preceded
        # by a backslash);
        r = list()
        assert correct_email('john(smith@example.com', False, r) == ('johnsmith@example.com', True)
        assert r == ["4:("]
        r = list()
        assert correct_email('"john(smith"@example.com', False, r) == ('"john(smith"@example.com', False)
        assert r == []

    def test_all_contacts(self, salesforce_connection):
        assert salesforce_connection.error_msg == ""
        contacts = salesforce_connection.contacts_with_rci_id(EXT_REFS_SEP)
        assert salesforce_connection.error_msg == ""
        for c in contacts:
            print(c)
            assert len(c) == 5  # tuple items: (CD_CODE, Sf_Id, Sihot_Guest_Object_Id, RCI refs, is_owner)
            assert len(c[1]) == 18
            assert isinstance(c[3], str)
            assert len(c[3]) > 0
            rci_ids = c[3].split(EXT_REFS_SEP)
            assert len(rci_ids) > 0
            for rci_id in rci_ids:
                assert rci_id not in self.sf_id_of_rci_id.items()
                self.sf_id_of_rci_id[rci_id] = c[1]

        # now check if the contact can be found by the rci_id
        print(repr(self.sf_id_of_rci_id))
        for rci_id in self.sf_id_of_rci_id:
            sf_id, duplicates = salesforce_connection.contact_by_rci_id(rci_id)
            # print(rci_id, sf_id, duplicates)
            assert sf_id == self.sf_id_of_rci_id[rci_id]
            assert isinstance(duplicates, list)
