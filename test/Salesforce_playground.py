from ae_console_app import ConsoleApp, DEBUG_LEVEL_VERBOSE
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed, SalesforceResourceNotFound

__version__ = '0.1'

cae = ConsoleApp(__version__, "Salesforce Playground", debug_level_def=DEBUG_LEVEL_VERBOSE,
                 additional_cfg_files=['../.console_app_env.cfg'])

cae.add_option('sfUser', "Salesforce account user name", '', 'y')
cae.add_option('sfPassword', "Salesforce account user password", '', 'a')
cae.add_option('sfToken', "Salesforce account token string", '', 'o')
cae.add_option('sfClientId', "Salesforce client/application name/id", cae.app_name(), 'c')
cae.add_option('sfIsSandbox', "Use Salesforce sandbox (instead of production)", True, 's')

sf_user = cae.get_option('sfUser')
sf_pw = cae.get_option('sfPassword')
sf_token = cae.get_option('sfToken')

sb = Salesforce(username=sf_user, password=sf_pw, security_token=sf_token, sandbox=True, client_id='ResImport')
print('Salesforce object:', sb)

print('Top-level objects describe:', sb.describe())

print('Opportunity metadata:', sb.Opportunity.metadata())

# OLD
print('Contact metadata:', sb.Contact.metadata())
print('Contact describe:', sb.Contact.describe())

print('External_Ref metadata:', sb.External_Ref__c.metadata())
print('External_Ref describe:', sb.External_Ref__c.describe())

result = sb.query_all("SELECT Id, Email FROM Contact WHERE LastName = 'Pepper'")
print('SOQL query:', result)

contact = sb.search("FIND {Pepper}")
print('SOSL search:', contact)

contact_id = contact['searchRecords'][0]['Id']
print('Contact Id:', contact_id)

c_data = sb.Contact.get(contact_id)
print('Contact data:', c_data)

c_with_rci = sb.search("FIND {1234\-56789}")
print('SOSL ext refs custom object search for RCI ref:', c_with_rci)

c_with_acu = sb.search("FIND {T123456}")
print('SOSL custom field search for Acumen ref:', c_with_acu)

c_data2 = sb.Contact.get_by_custom_id('CD_CODE__c', 'T654321')
print('Contact data by Acumen ref. custom field:', c_data2)

# the RCI_Reference__c custom field is NOT an External ID
try:
    c_data2 = sb.Contact.get_by_custom_id('RCI_Reference__c', '9876\-54321')
except SalesforceResourceNotFound as ex:
    print('  ****  RCI_Reference__c custom field is not an External Id  ****  ', ex)
else:
    print('Contact data fetched via RCI ref. custom field:', c_data2)

try:
    c_data3 = sb.External_Ref__c.get(contact_id)
except SalesforceResourceNotFound as ex:
    print('  ****  Reference_Ref__c custom object is not fetch-able  ****  ', ex)
else:
    print("External Ref data fetched via contact_id", c_data3)

try:
    c_data2 = sb.Contact.get_by_custom_id('Reference_No_or_ID__c', '1234\-56789')
except SalesforceResourceNotFound as ex:
    print('  ****  Reference_No_or_ID__c custom field is not an External Id  ****  ', ex)
else:
    print('Contact data fetched via RCI ref custom object field:', c_data2)

try:
    c_data2 = sb.External_Ref__c.get_by_custom_id('Reference_No_or_ID__c', '1234\-56789')
except SalesforceResourceNotFound as ex:
    print('  ****  Reference_No_or_ID__c custom field not found via External_Ref custom object  ****  ', ex)
else:
    print('External Ref data fetched via RCI ref custom object field:', c_data2)

try:
    c_data2 = sb.Contact.get_by_custom_id('Reference_No_or_ID__c', '1234\-56789')
except SalesforceResourceNotFound as ex:
    print('  ****  Reference_No_or_ID__c custom field not found via Contact object  ****  ', ex)
else:
    print('Contact data fetched via RCI ref custom object field:', c_data2)

try:
    c_data2 = sb.External_Ref__c.get_by_custom_id('Reference_No_or_ID__c', '1234*')
except SalesforceResourceNotFound as ex:
    print('  ****  Reference_No_or_ID__c custom field not found via External_Ref custom object  ****  ', ex)
else:
    print('External Ref data fetched via RCI ref custom object field:', c_data2)

try:
    c_data2 = sb.Contact.get_by_custom_id('Reference_No_or_ID__c', '1234*')
except SalesforceResourceNotFound as ex:
    print('  ****  Reference_No_or_ID__c custom field not found via Contact object  ****  ', ex)
else:
    print('Contact data fetched via RCI ref custom object field:', c_data2)

result = sb.query_all("SELECT Id, Reference_No_or_ID__c FROM External_Ref__c WHERE Reference_No_or_ID__c like '1234%'")
print('SOQL like query:', result)

result = sb.query_all("SELECT Id FROM External_Ref__c WHERE Reference_No_or_ID__c = '1234-56789'")
print('SOQL exact query Pepper:', result)

result = sb.query_all("SELECT Id FROM External_Ref__c WHERE Reference_No_or_ID__c = 'abcd-efgh'")
print('SOQL exact query Testa123:', result)

ext_ref = sb.search("FIND {1234\-5678*}")
print('SOSL like ext ref search:', ext_ref)

ext_ref = sb.search("FIND {1234*}")
print('SOSL like ext ref search:', ext_ref)

ext_ref = sb.search("FIND {RCI_1}")
print('SOSL exact ext ref name search:', ext_ref)

ext_ref = sb.search("FIND {RCI}")
print('SOSL exact ext ref type search:', ext_ref)

ext_ref = sb.search("FIND {1234\-56789}")
print('SOSL exact ext ref search:', ext_ref)

ext_ref_id = [_['Id'] for _ in ext_ref['searchRecords'] if _['attributes']['type'] == 'External_Ref__c'][0]
ext_ref_data = sb.External_Ref__c.get(ext_ref_id)
print('Ext Ref Data:', ext_ref_data)

ext_ref_contact = ext_ref_data['Contact__c']
contact_data = sb.Contact.get(ext_ref_contact)
print('Contact data fetched via RCI ref:', contact_data)

result = sb.query_all("SELECT Id FROM External_Ref__c WHERE Contact__c = '" + ext_ref_contact + "'")
print('SOQL query fetching all external ref IDs from Pepper:', result)

records = result['records']  # list of OrderedDict with Id item/key
rec_ids = [_['Id'] for _ in records]
print('Ext Ref Ids of last SOQL query:', rec_ids)

result = sb.query_all("SELECT Reference_No_or_ID__c FROM External_Ref__c WHERE Contact__c = '" + ext_ref_contact + "'")
print('SOQL query fetching all external ref numbers from Pepper:', result)

records = result['records']  # list of OrderedDict with external ref no
rec_nos = [_['Reference_No_or_ID__c'] for _ in records]
print('Ext Ref numbers of last SOQL query:', rec_nos)

new_no = '1234-8902'
if new_no in rec_nos:
    print('  ####  External ref no ', new_no, 'already created for Pepper with ID', ext_ref_contact)
else:
    ret = sb.External_Ref__c.create({'Contact__c': ext_ref_contact, 'Reference_No_or_ID__c': new_no,
                                     # 'Type__c': 'RCI',
                                     'Name': 'RCI_9'})
    print('Created Ext Ref return1:', ret)

new_no = 'abcd-7890'
test_contact_id = '0039E00000Dla2VQAR'  # (test_contact_id in contacts) fails with 15 character ID == '0039E00000Dla2V'
result = sb.query_all("SELECT Id, Contact__c FROM External_Ref__c WHERE Reference_No_or_ID__c = '" + new_no + "'")
print('SOQL querying RCI ref number from Testa:', result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] for _ in records]
    print('Ext Ref Ids of last SOQL query:', ids)
    contacts = [_['Contact__c'] for _ in records]
    print('Ext Ref Contact Ids of last SOQL query:', contacts)

    if test_contact_id in contacts:
        print('  ####  External RCI ref number', new_no, 'already exists for Testa client with ID', test_contact_id)
    else:
        ret = sb.External_Ref__c.create({'Contact__c': test_contact_id, 'Reference_No_or_ID__c': new_no,
                                         # 'Type__c': 'RCI',
                                         'Name': 'RCI_88'})
        print('    Created Ext Ref return2 for Testa:', ret)
        if ret['success']:
            ret = sb.External_Ref__c.upsert(ret['id'],
                                            {'Name': 'RCI_8'})
            print('        Upsert Ext Ref return3 for Testa(changed RCI_88 to RCI_8):', ret)
elif result['done']:
    print('  ####  last SOQL query done but no records found, totalSize=', result['totalSize'])
else:
    print('  ****  last SOQL query failed to be executed/done completely')

result = sb.query_all("SELECT Id FROM Contact WHERE RCI_Reference__c = 'abcd-9876'")
print('SOQL querying main RCI ref number (abcd-9876) from Testa:', result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] for _ in records]
    print('    Ext Ref Ids of last SOQL query:', ids)

result = sb.query_all("SELECT Contact__c, Id FROM External_Ref__c WHERE Name LIKE 'RCI%'")
print("SOQL querying Contact Ids with external RCI Ids", result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    contacts = [_['Contact__c'] + '=' + _['Id'] for _ in records]
    print('    Ext Ref Contact Ids with RCI Id of last SOQL query:', contacts)

result = sb.query_all("SELECT Contact__c FROM External_Ref__c WHERE Name LIKE 'RCI%' GROUP BY Contact__c")
print("SOQL querying distinct Contact Ids with external RCI Ids", result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    contacts = [_['Contact__c'] for _ in records]
    print('    Ext Ref Contact Ids of last SOQL query:', contacts)

result = sb.query_all("SELECT Id FROM Contact WHERE RCI_Reference__c != NULL")
print('SOQL querying Contact Ids with main RCI Ids', result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] for _ in records]
    print('    Contact Ids with main RCI Refs of last SOQL query:', ids)

# next query results in error: Semi join sub-selects are not allowed with the 'OR' operator
# result = sb.query_all("SELECT Id, CD_CODE__c, RCI_Reference__c FROM Contact WHERE RCI_Reference__c != NULL"
#                      " or Id in (SELECT Contact__c FROM External_Ref__c WHERE Name LIKE 'RCI%')")
result = sb.query_all("SELECT Id, CD_CODE__c, RCI_Reference__c,"
                      " (SELECT Reference_No_or_ID__c, Name FROM External_References__r)"
                      " FROM Contact"
                      " WHERE RCI_Reference__c != NULL")
print('SOQL querying Contact data with main or external RCI Ids', result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] + '=' + er['Reference_No_or_ID__c'] for _ in records for er in _['External_References__r']['records']]
    print('    Ext Ref Ids of last SOQL query:', ids)

# .. same as above restricted to external RCI refs
# .. and without duplicates (but SF doesn't support GROUP BY Reference_No_or_ID__c in sub-query)
result = sb.query_all("SELECT Id, CD_CODE__c, RCI_Reference__c,"
                      " (SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%')"
                      " FROM Contact"
                      " WHERE RCI_Reference__c != NULL")
                      # SF doesn't allow sub-queries in WHERE clause
                      # " or (SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%') != NULL")
print('SOQL querying Contact data with unique main or external RCI Ids', result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] + '=' + er['Reference_No_or_ID__c'] for _ in records for er in _['External_References__r']['records']]
    print('    Ext Ref Ids of unique SOQL query:', ids)


# SOQL query to include record type of contact
result = sb.query_all("SELECT Id, Name, RecordType.DeveloperName FROM Contact WHERE LastName = 'Pepper'")
if result['done'] and result['totalSize'] > 0:
    records = result['records']
    rec_type = records[0]['RecordType']['DeveloperName']
    print("Fetch contact data with RecordType", rec_type, records)

# check create/update/delete of Contact object
result = sb.query_all("Select Id From RecordType Where SobjectType = 'Contact' and DeveloperName = 'Rentals'")
if result['done'] and result['totalSize'] > 0:
    rec_type = result['records'][0]['Id']
    print("RecordTypeId=", rec_type)    # == '0129E000000CmLVQA0'
    email = 'y_u_h_u@yahoo.com'
    sb.error_message = ''
    result = sb.query_all("SELECT Id FROM Contact WHERE Email = '" + email + "'")
    if result['done']:
        if result['totalSize'] > 0:
            print(".. updating")
            sb.Contact.update(result['records'][0]['Id'],
                              {'FirstName': 'Sally', 'lastName': 'S-force', 'RecordTypeId': rec_type,
                               'Email': email, 'Birthdate': '1952-6-18', 'Description': None})
        else:
            print(".. inserting")
            sb.Contact.create({'FirstName': 'Sally', 'lastName': 'S-force', 'RecordTypeId': rec_type,
                               'Email': email, 'Birthdate': '1962-6-18'})
        if sb.error_message:
            print("Salesforce error:", sb.error_message)

# extract data for to double check phone validation done with data-8 against the byteplant phone validator
result = sb.query_all("SELECT Id, Country__c, HomePhone, MobilePhone, Work_Phone__c,"
                      " CD_Htel_valid__c, CD_mtel_valid__c, CD_wtel_valid__c"
                      " FROM Contact"
                      " WHERE CD_Htel_valid__c != NULL or CD_mtel_valid__c != NULL or CD_wtel_valid__c != NULL")
if result['done'] and result['totalSize'] > 0:
    records = result['records']
    for rec in records:
        print(rec['Id'], rec['Country__c'],
              rec['HomePhone'], rec['CD_Htel_valid__c'], rec['MobilePhone'], rec['CD_mtel_valid__c'],
              rec['Work_Phone__c'], rec['CD_wtel_valid__c'])
