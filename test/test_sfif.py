from sfif import correct_email, correct_phone
from ass_sys_data import EXT_REFS_SEP


class TestSfFindClient:
    def test_not_existing_client(self, salesforce_connection):
        sfi = salesforce_connection
        result = sfi.find_client(email="test@test.test", phone="0034922777888", first_name="Testy", last_name="Tester")
        print('Encapsulated APEX REST call result', result)
        assert 'id' in result
        assert result['id'] == ''
        assert 'type' in result
        assert result['type'] == 'None'

    def test_identify_by_email(self, salesforce_connection):
        sfi = salesforce_connection
        sf_id, err, msg = sfi.contact_upsert(fields_dict=dict(firstName="Testy", lastName="Tester",
                                                              Email="clienthasnoemail@test.com"))
        print("test_by_invalid_email() sf_id/err/msg:", sf_id, err, msg)
        assert len(sf_id) == 18
        assert err == ""

        result = sfi.find_client(email="clienthasnoemail@test.com", first_name="Testy", last_name="Tester")
        print('Encapsulated APEX REST call result', result)

        # before checking we need first to delete the test client
        assert sfi.contact_delete(sf_id)[0]

        assert 'id' in result
        assert len(result['id']) == 18
        assert result['id'] == sf_id
        assert 'type' in result
        assert result['type'] == 'Contact'


class TestSfContact:
    sf_id_of_rci_id = dict()

    def test_correct_email(self):
        # edge cases: empty string or None as email
        r = list()
        assert correct_email('', False, r) == ('', False)
        assert r == []
        r = list()
        assert correct_email(None, False, r) == (None, False)
        assert r == []
        # special characters !#$%&'*+-/=?^_`{|}~; are allowed in local part
        r = list()
        assert correct_email('john_smith@example.com', False, r) == ('john_smith@example.com', False)
        assert r == []
        r = list()
        assert correct_email('john?smith@example.com', False, r) == ('john?smith@example.com', False)
        assert r == []

        # dot is not the first or last character unless quoted, and does not appear consecutively unless quoted
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
        r = list()
        assert correct_email("john.smith@example..com", False, r) == ("john.smith@example.com", True)
        assert r == ["19:."]

        # space and "(),:;<>@[\] characters are allowed with restrictions (they are only allowed inside a quoted string,
        # as described in the paragraph below, and in addition, a backslash or double-quote must be preceded
        # by a backslash);
        r = list()
        assert correct_email(" john.smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["0: "]
        r = list()
        assert correct_email("john .smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["4: "]
        r = list()
        assert correct_email("john.smith @example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["10: "]
        r = list()
        assert correct_email("john.smith@ example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["11: "]
        r = list()
        assert correct_email("john.smith@ex ample.com", False, r) == ("john.smith@example.com", True)
        assert r == ["13: "]
        r = list()
        assert correct_email("john.smith@example .com", False, r) == ("john.smith@example.com", True)
        assert r == ["18: "]
        r = list()
        assert correct_email("john.smith@example. com", False, r) == ("john.smith@example.com", True)
        assert r == ["19: "]
        r = list()
        assert correct_email("john.smith@example.com  ", False, r) == ("john.smith@example.com", True)
        assert r == ["22: ", "23: "]
        r = list()
        assert correct_email('john(smith@example.com', False, r) == ('johnsmith@example.com', True)
        assert r == ["4:("]
        r = list()
        assert correct_email('"john(smith"@example.com', False, r) == ('"john(smith"@example.com', False)
        assert r == []

        # comments at begin or end of local and domain part
        r = list()
        assert correct_email("john.smith(comment)@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["10:(comment)"]
        r = list()
        assert correct_email("(comment)john.smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["0:(comment)"]
        r = list()
        assert correct_email("john.smith@example.com(comment)", False, r) == ("john.smith@example.com", True)
        assert r == ["22:(comment)"]
        r = list()
        assert correct_email("john.smith@(comment)example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["11:(comment)"]
        r = list()
        assert correct_email(".john.smith@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["0:."]
        r = list()
        assert correct_email("john.smith.@example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["10:."]
        r = list()
        assert correct_email("john.smith@.example.com", False, r) == ("john.smith@example.com", True)
        assert r == ["11:."]
        r = list()
        assert correct_email("john.smith@example.com.", False, r) == ("john.smith@example.com", True)
        assert r == ["22:."]

        # international characters above U+007F
        r = list()
        assert correct_email('Heinz.Hübner@example.com', False, r) == ('Heinz.Hübner@example.com', False)
        assert r == []

        # quoted may exist as a dot separated entity within the local-part, or it may exist when the outermost
        # .. quotes are the outermost characters of the local-part
        r = list()
        assert correct_email('abc."def".xyz@example.com', False, r) == ('abc."def".xyz@example.com', False)
        assert r == []
        assert correct_email('"abc"@example.com', False, r) == ('"abc"@example.com', False)
        assert r == []
        assert correct_email('abc"def"xyz@example.com', False, r) == ('abcdefxyz@example.com', True)
        assert r == ['3:"', '7:"']

        # tests from https://en.wikipedia.org/wiki/Email_address
        r = list()
        assert correct_email('ex-indeed@strange-example.com', False, r) == ('ex-indeed@strange-example.com', False)
        assert r == []
        r = list()
        assert correct_email("#!$%&'*+-/=?^_`{}|~@example.org", False, r) == ("#!$%&'*+-/=?^_`{}|~@example.org", False)
        assert r == []
        r = list()
        assert correct_email('"()<>[]:,;@\\\\"!#$%&\'-/=?^_`{}| ~.a"@e.org', False, r) \
            == ('"()<>[]:,;@\\\\"!#$%&\'-/=?^_`{}| ~.a"@e.org', False)
        assert r == []

        r = list()
        assert correct_email("A@e@x@ample.com", False, r) == ("A@example.com", True)
        assert r == ["3:@", "5:@"]
        r = list()
        assert correct_email('this\ is\"not\\allowed@example.com', False, r) == ('thisisnotallowed@example.com', True)
        assert r == ["4:\\", "5: ", '8:"', '12:\\']

    def test_correct_phone(self):
        r = list()
        assert correct_phone('+4455667788', False, r) == ('004455667788', True)
        assert r == ["0:+"]

        r = list()
        assert correct_phone(' +4455667788', False, r) == ('004455667788', True)
        assert r == ["0: ", "1:+"]

        r = list()
        assert correct_phone('+004455667788', False, r) == ('004455667788', True)
        assert r == ["0:+"]

        r = list()
        assert correct_phone(' 44 5566/7788', False, r) == ('4455667788', True)
        assert r == ["0: ", "3: ", "8:/"]

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
