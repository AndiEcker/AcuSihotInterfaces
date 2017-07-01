from ae_console_app import ConsoleApp, DEBUG_LEVEL_VERBOSE
from simple_salesforce import Salesforce, SalesforceResourceNotFound

__version__ = '0.1'

cae = ConsoleApp(__version__, "Import reservations from external systems (Thomas Cook, RCI) into the SiHOT-PMS",
                 debug_level_def=DEBUG_LEVEL_VERBOSE)

sf_user = cae.get_config('sfUser')
sf_sandbox_user = cae.get_config('sfSandboxUser')
sf_pw = cae.get_config('sfPassword')
sf_token = cae.get_config('sfToken')

sb = Salesforce(username=sf_sandbox_user, password=sf_pw, security_token=sf_token, sandbox=True)

print('Contact metadata:', sb.Contact.metadata())
print('Contact describe:', sb.Contact.describe())

print('External_Ref metadata:', sb.External_Ref__c.metadata())
print('External_Ref describe:', sb.External_Ref__c.describe())

result = sb.query_all("SELECT Id, Email FROM Contact WHERE LastName = 'Pepper'")
print('SOQL query:', result)

contact = sb.search("FIND {Pepper}")
print('SOSL search:', contact)

contact_id = contact[0]['Id']
print('Contact Id:', contact_id)

c_data = sb.Contact.get(contact_id)
print('Contact data:', c_data)

c_with_rci = sb.search("FIND {1234\-56789}")
print('SOSL ext refs custom object search for RCI ref:', c_with_rci)

c_with_acu = sb.search("FIND {T123456}")
print('SOSL custom field search for Acumen ref:', c_with_acu)

c_data2 = sb.Contact.get_by_custom_id('CD_CODE__c', 'T123456')
print('Contact data by Acumen ref. custom field:', c_data2)

# the RCI_Reference__c custom field is NOT an External ID
try:
    c_data2 = sb.Contact.get_by_custom_id('RCI_Reference__c', '9876\-54321')
except SalesforceResourceNotFound:
    print('  ****  RCI_Reference__c custom field is not an External Id')
else:
    print('Contact data fetched via RCI ref. custom field:', c_data2)

try:
    c_data3 = sb.External_Ref__c.get(contact_id)
except SalesforceResourceNotFound:
    print('  ****  Reference_Ref__c custom object is not fetch-able')
else:
    print("External Ref data fetched via contact_id", c_data3)

try:
    c_data2 = sb.Contact.get_by_custom_id('Reference_No_or_ID__c', '1234\-56789')
except SalesforceResourceNotFound:
    print('  ****  Reference_No_or_ID__c custom field is not an External Id')
else:
    print('Contact data fetched via RCI ref custom object field:', c_data2)

