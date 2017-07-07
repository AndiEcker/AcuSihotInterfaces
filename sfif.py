from simple_salesforce import Salesforce, SalesforceAuthenticationFailed


class SfInterface:
    def __init__(self, username, password, token, sandbox):
        self.conn = None
        self.error_msg = ""
        try:
            self.conn = Salesforce(username=username, password=password, security_token=token, sandbox=sandbox)
        except SalesforceAuthenticationFailed as sf_ex:
            self.error_msg = "SfInterface.__init__(): Salesforce{} authentication failed with exception: {}" \
                .format(' (sandbox)' if sandbox else '', sf_ex)

    def contacts_with_rci_id(self):
        contacts = []
        try:
            r = self.conn.query_all("SELECT Id, CD_CODE__c, RCI_Reference__c,"
                                    " (SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%')"
                                    " FROM Contact")
        except Exception as sf_ex:
            self.error_msg = "SfInterface.contact_by_rci_id() exception: {}".format(sf_ex)
            return contacts

        if r['done'] and r['totalSize'] > 0:
            for contact in r['records']:  # list of Contact OrderedDicts
                refs = [contact['RCI_Reference__c']] if contact['RCI_Reference__c'] else []
                refs.extend([er['Reference_No_or_ID__c'] for er in contact['External_References__r']['records']])
                if refs:
                    contacts.append((contact['Id'], contact['CD_CODE__c'], set(refs)))
        return contacts

    REF_TYPE_ALL = 'all'
    REF_TYPE_MAIN = 'main'
    REF_TYPE_EXT = 'external'

    def contact_by_rci_id(self, imp_rci_ref, sf_contact_id=None, dup_contacts=None, which_ref=REF_TYPE_ALL):
        if not dup_contacts:
            dup_contacts = []
        if which_ref in (self.REF_TYPE_MAIN, self.REF_TYPE_ALL):
            soql_query = "SELECT Id FROM Contact WHERE RCI_Reference__c = '{}'".format(imp_rci_ref)
            col_name = 'Id'
        else:   # which_ref == REF_TYPE_EXT
            soql_query = "SELECT Contact__c FROM External_Ref__c WHERE Reference_No_or_ID__c = '{}'".format(imp_rci_ref)
            col_name = 'Contact__c'
        try:
            result = self.conn.query_all(soql_query)
        except Exception as sf_ex:
            self.error_msg = "SfInterface.contact_by_rci_id() exception: {}".format(sf_ex)
        else:
            if result['done'] and result['totalSize'] > 0:
                if not sf_contact_id:
                    sf_contact_id = result['records'][0][col_name]
                if result['totalSize'] > 1:
                    new_contacts = [_[col_name] for _ in result['records']]
                    dup_contacts = list(set([_ for _ in new_contacts + dup_contacts if _ != sf_contact_id]))
        if which_ref == self.REF_TYPE_ALL:
            sf_contact_id, dup_contacts = self.contact_by_rci_id(imp_rci_ref, sf_contact_id, dup_contacts,
                                                                 self.REF_TYPE_EXT)
        return sf_contact_id, dup_contacts
