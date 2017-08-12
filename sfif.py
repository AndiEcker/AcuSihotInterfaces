from simple_salesforce import Salesforce, SalesforceAuthenticationFailed, SalesforceExpiredSession
from ae_console_app import uprint

# contact record type id for owners
OWNER_RECORD_TYPE_ID = '012w0000000MSyZAAW'  # 15 digit ID == 012w0000000MSyZ


def prepare_connection(cae, client_id='', use_production=False, print_on_console=False):
    sf_sandbox = cae.get_config('sfIsSandbox', default_value=not use_production)
    if sf_sandbox == use_production:
        uprint('******  Salesforce sandbox/production usage discrepancy: sandbox={}, use_production={}'
               .format(sf_sandbox, use_production))
        sf_sandbox = not use_production

    suffix = 'Production' if use_production else ''
    sf_user = cae.get_config('sfUser' + suffix, default_value=cae.get_config('sfUser', default_value=''))
    sf_client = cae.get_config('sfClientId' + suffix,
                               default_value=cae.get_config('sfClientId', default_value=client_id))
    sf_token = cae.get_config('sfToken' + suffix, default_value=cae.get_config('sfToken', default_value=''))
    sf_pw = cae.get_config('sfPassword' + suffix, default_value=cae.get_config('sfPassword', default_value=''))
    sf_conn = SfInterface(sf_user, sf_pw, sf_token, sf_sandbox, sf_client)
    if print_on_console:
        uprint("Salesforce " + ("sandbox" if sf_sandbox else "production") + " user/client-id:", sf_user, sf_client)

    return sf_conn, sf_sandbox


class SfInterface:
    def __init__(self, username, password, token, sandbox, client_id='SignalliaSfInterface'):
        # store user credentials for lazy Salesforce connect (only if needed) because of connection limits and timeouts
        self._conn = None
        self._user = username
        self._pw = password
        self._tok = token
        self._sb = sandbox
        self._client = client_id

        self.error_msg = ""

    def _connect(self):
        try:
            self._conn = Salesforce(username=self._user, password=self._pw, security_token=self._tok,
                                    sandbox=self._sb, client_id=self._client)
        except SalesforceAuthenticationFailed as sf_ex:
            self.error_msg = "SfInterface.__init__(): Salesforce{} authentication failed with exception: {}" \
                .format(' (sandbox)' if self._sb else '', sf_ex)
        else:
            self.error_msg = ""

    def _soql_query_all(self, soql_query):
        self.error_msg = ""
        if not self._conn:
            self._connect()
            if self.error_msg:
                return None
        response = None
        try:
            response = self._conn.query_all(soql_query)
        except SalesforceExpiredSession:
            print("  **  Trying to re-connect expired Salesforce session...")
            self._connect()
            try:
                response = self._conn.query_all(soql_query)
            except Exception as sf_ex:
                self.error_msg = "SfInterface._soql_query_all({}) re-connect exception: {}".format(soql_query, sf_ex)
        except Exception as sf_ex:
            self.error_msg = "SfInterface._soql_query_all({}) query exception: {}".format(soql_query, sf_ex)
        if response and not response['done']:
            self.error_msg = "SfInterface._soql_query_all(): Salesforce is responding that query {} is NOT done." \
                .format(soql_query)
        return response

    def sf_types(self):
        if not self._conn:
            self._connect()
            if self.error_msg:
                return None
        return self._conn

    def contacts_with_rci_id(self, ext_refs_sep):
        contact_tuples = []
        res = self._soql_query_all("SELECT Id, CD_CODE__c, RCI_Reference__c, Sihot_Guest_Object_Id__c, RecordType.Id,"
                                   " (SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%')"
                                   " FROM Contact")
        if not self.error_msg and res['totalSize'] > 0:
            for c in res['records']:  # list of Contact OrderedDicts
                ext_refs = [c['RCI_Reference__c']] if c['RCI_Reference__c'] else []
                ext_refs.extend([_['Reference_No_or_ID__c'] for _ in c['External_References__r']['records']])
                if ext_refs:
                    contact_tuples.append((c['CD_CODE__c'], c['Id'], c['Sihot_Guest_Object_Id__c'],
                                          ext_refs_sep.join(ext_refs),
                                          1 if c['RecordType']['Id'] == OWNER_RECORD_TYPE_ID else 0))
        return contact_tuples

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
        res = self._soql_query_all(soql_query)
        if not self.error_msg and res['totalSize'] > 0:
            if not sf_contact_id:
                sf_contact_id = res['records'][0][col_name]
            if res['totalSize'] > 1:
                new_contacts = [_[col_name] for _ in res['records']]
                dup_contacts = list(set([_ for _ in new_contacts + dup_contacts if _ != sf_contact_id]))

        if which_ref == self.REF_TYPE_ALL:
            sf_contact_id, dup_contacts = self.contact_by_rci_id(imp_rci_ref, sf_contact_id, dup_contacts,
                                                                 self.REF_TYPE_EXT)
        return sf_contact_id, dup_contacts

    def contact_by_email(self, email):
        soql_query = "SELECT Id FROM Contact WHERE Email = '{}'".format(email)
        res = self._soql_query_all(soql_query)
        if not self.error_msg and res['totalSize'] > 0:
            return res['records'][0]['Id']
        return None

    def contact_sh_id(self, sf_contact_id):
        sh_id = None
        res = self._soql_query_all("SELECT Sihot_Guest_Object_Id__c FROM Contact WHERE Id = '{}'".format(sf_contact_id))
        if not self.error_msg and res['totalSize'] > 0:
            sh_id = res['records'][0]['Sihot_Guest_Object_Id__c']
        return sh_id

    def contact_data_by_id(self, sf_contact_id, field_names):
        sf_dict = dict()
        res = self._soql_query_all("SELECT " + ", ".join(field_names) + " FROM Contact WHERE Id = '{}'"
                                   .format(sf_contact_id))
        if not self.error_msg and res['totalSize'] > 0:
            sf_dict = res['records'][0]
        return sf_dict

    def contacts_not_validated(self, rec_type_dev_name=None, validate_email=True, validate_phone=False):
        assert validate_email or validate_phone
        q = "SELECT Id, Country__c" \
            + (", Email, CD_email_valid__c" if validate_email else "") \
            + (", HomePhone, CD_Htel_valid__c, MobilePhone, CD_mtel_valid__c, Work_Phone__c, CD_wtel_valid__c"
               if validate_phone else "") \
            + " FROM Contact WHERE" \
            + (" RecordType.DeveloperName = '" + rec_type_dev_name + "' and" if rec_type_dev_name else "") \
            + "(" \
            + ("(Email != Null and CD_email_valid__c = NULL)" if validate_email else "") \
            + (" or " if validate_email and validate_phone else "") \
            + ("(HomePhone != NULL and CD_Htel_valid__c = NULL)"
               + " or (MobilePhone != NULL and CD_mtel_valid__c = NULL)"
               + " or (Work_Phone__c != NULL and CD_wtel_valid__c = NULL)" if validate_phone else "") \
            + ") ORDER BY Country__c"
        res = self._soql_query_all(q)
        if self.error_msg or res['totalSize'] <= 0:
            contact_dicts = []
        else:
            contact_dicts = [{k: v for k, v in rec.items() if k != 'attributes'} for rec in res['records']]
            assert len(contact_dicts) == res['totalSize']
        return contact_dicts

    def contact_upsert(self, fields_dict):
        err = msg = ""
        if 'Id' in fields_dict:     # update?
            sf_id = fields_dict['Id']
            del fields_dict['Id']
            try:
                sf_http_code = self._conn.Contact.update(sf_id, fields_dict)
                msg = "Salesforce Contact {} updated with {}, status={}".format(sf_id, fields_dict, sf_http_code)
            except Exception as ex:
                err = "Salesforce Contact update raised exception {}".format(ex)
        else:
            try:
                sf_http_code = self._conn.Contact.create(fields_dict)
                msg = "Salesforce Contact created with {}, status={}".format(fields_dict, sf_http_code)
            except Exception as ex:
                err = "Salesforce Contact creation raised exception {}".format(ex)
        return err, msg

    def record_type_id(self, dev_name, obj_type='Contact'):
        rec_type_id = None
        res = self._soql_query_all("Select Id From RecordType Where SobjectType = '{}' and DeveloperName = '{}'"
                                   .format(obj_type, dev_name))
        if not self.error_msg and res['totalSize'] > 0:
            rec_type_id = res['records'][0]['Id']
        return rec_type_id
