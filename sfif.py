from simple_salesforce import Salesforce, SalesforceAuthenticationFailed

# contact record type id for owners
OWNER_RECORD_TYPE_ID = '012w0000000MSyZAAW'  # 15 digit ID == 012w0000000MSyZ


class SfInterface:
    def __init__(self, username, password, token, sandbox):
        self.conn = None
        self.error_msg = ""
        try:
            self.conn = Salesforce(username=username, password=password, security_token=token, sandbox=sandbox)
        except SalesforceAuthenticationFailed as sf_ex:
            self.error_msg = "SfInterface.__init__(): Salesforce{} authentication failed with exception: {}" \
                .format(' (sandbox)' if sandbox else '', sf_ex)

    def contacts_with_rci_id(self, ext_refs_sep):
        contacts = []
        try:
            r = self.conn.query_all("SELECT Id, CD_CODE__c, RCI_Reference__c, Sihot_Guest_Object_Id__c, RecordType.Id,"
                                    " (SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%')"
                                    " FROM Contact")
        except Exception as sf_ex:
            self.error_msg = "SfInterface.contacts_with_rci_id() exception: {}".format(sf_ex)
        else:
            if not r['done']:
                self.error_msg = "SfInterface.contacts_with_rci_id(): Salesforce is responding not DONE."
            else:
                self.error_msg = ""
                if r['totalSize'] > 0:
                    for c in r['records']:  # list of Contact OrderedDicts
                        ext_refs = [c['RCI_Reference__c']] if c['RCI_Reference__c'] else []
                        ext_refs.extend([_['Reference_No_or_ID__c'] for _ in c['External_References__r']['records']])
                        if ext_refs:
                            contacts.append((c['CD_CODE__c'], c['Id'], c['Sihot_Guest_Object_Id__c'],
                                             ext_refs_sep.join(ext_refs),
                                             1 if c['RecordType']['Id'] == OWNER_RECORD_TYPE_ID else 0))
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
            if not result['done']:
                self.error_msg = "SfInterface.contact_by_rci_id(): Salesforce is responding NOT DONE."
            else:
                self.error_msg = ""
                if result['totalSize'] > 0:
                    if not sf_contact_id:
                        sf_contact_id = result['records'][0][col_name]
                    if result['totalSize'] > 1:
                        new_contacts = [_[col_name] for _ in result['records']]
                        dup_contacts = list(set([_ for _ in new_contacts + dup_contacts if _ != sf_contact_id]))
        if which_ref == self.REF_TYPE_ALL:
            sf_contact_id, dup_contacts = self.contact_by_rci_id(imp_rci_ref, sf_contact_id, dup_contacts,
                                                                 self.REF_TYPE_EXT)
        return sf_contact_id, dup_contacts

    def contact_sh_id(self, sf_contact_id):
        sh_id = None
        soql_query = "SELECT Sihot_Guest_Object_Id__c FROM Contact WHERE Id = '{}'".format(sf_contact_id)
        try:
            result = self.conn.query_all(soql_query)
        except Exception as sf_ex:
            self.error_msg = "SfInterface.contact_sh_id() exception: {}".format(sf_ex)
        else:
            if not result['done']:
                self.error_msg = "SfInterface.contact_sh_id(): Salesforce is responding NOT done."
            else:
                self.error_msg = ""
                if result['totalSize'] > 0:
                    sh_id = result['records'][0]['Sihot_Guest_Object_Id__c']
        return sh_id
