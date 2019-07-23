import pprint
from collections import OrderedDict

from ae import DEBUG_LEVEL_VERBOSE
from ae.console_app import ConsoleApp
from simple_salesforce import Salesforce, SalesforceResourceNotFound
from sfif import add_sf_options

__version__ = '0.2'

cae = ConsoleApp(__version__, "Salesforce Playground", debug_level_def=DEBUG_LEVEL_VERBOSE,
                 additional_cfg_files=['../.console_app_env.cfg', '../.sys_envTEST.cfg'])

add_sf_options(cae)

sf_user = cae.get_option('sfUser')
sf_pw = cae.get_option('sfPassword')
sf_token = cae.get_option('sfToken')

sb = Salesforce(username=sf_user, password=sf_pw, security_token=sf_token, sandbox=True, client_id='ResImport')
print('Salesforce object:', sb)

print('Top-level objects describe:', pprint.pformat(sb.describe(), indent=3, compact=True))


print('Account metadata:', pprint.pformat(sb.Account.metadata(), indent=3, compact=True))
print('Contact metadata:', pprint.pformat(sb.Contact.metadata(), indent=3, compact=True))
print('Lead metadata:', pprint.pformat(sb.Lead.metadata(), indent=3, compact=True))
print('Opportunity metadata:', pprint.pformat(sb.Opportunity.metadata(), indent=3, compact=True))
print('Reservation metadata:', pprint.pformat(sb.Reservation__c.metadata(), indent=3, compact=True))
print('Allocation metadata:', pprint.pformat(sb.Allocation__c.metadata(), indent=3, compact=True))
print('External_Ref metadata:', pprint.pformat(sb.External_Ref__c.metadata(), indent=3, compact=True))

describe_txt = pprint.pformat(sb.Account.describe(), indent=3, compact=True)
with open('describe_account.log', 'w') as f:
    f.write(describe_txt)
print('Account describe:', describe_txt)

describe_txt = pprint.pformat(sb.Contact.describe(), indent=3, compact=True)
with open('describe_contact.log', 'w') as f:
    f.write(describe_txt)
print('Contact describe:', describe_txt)

describe_txt = pprint.pformat(sb.Lead.describe(), indent=3, compact=True)
with open('describe_lead.log', 'w') as f:
    f.write(describe_txt)
print('Lead describe:', describe_txt)

describe_txt = pprint.pformat(sb.Opportunity.describe(), indent=3, compact=True)
with open('describe_opportunity.log', 'w') as f:
    f.write(describe_txt)
print('Opportunity describe:', describe_txt)

describe_txt = pprint.pformat(sb.Reservation__c.describe(), indent=3, compact=True)
with open('describe_reservation.log', 'w') as f:
    f.write(describe_txt)
print('Reservation describe:', describe_txt)

describe_txt = pprint.pformat(sb.Allocation__c.describe(), indent=3, compact=True)
with open('describe_allocation.log', 'w') as f:
    f.write(describe_txt)
print('Allocation describe:', describe_txt)

describe_txt = pprint.pformat(sb.External_Ref__c.describe(), indent=3, compact=True)
with open('describe_external_ref.log', 'w') as f:
    f.write(describe_txt)
print('External_Ref describe:', describe_txt)


result = sb.query_all("SELECT Id, PersonEmail FROM Account WHERE LastName = 'Pepper'")
print('SOQL query:', result)
# noinspection SpellCheckingInspection
query_debug_result = OrderedDict([
    ('totalSize', 1),
    ('done', True),
    ('records', [OrderedDict([
        ('attributes', OrderedDict([('type', 'Account'),
                                    ('url', '/services/data/v38.0/sobjects/Account/0010O00001sKYf9QAG')])),
        ('Id', '0010O00001sKYf9QAG'),
        ('PersonEmail', 'jeffpep@hotmail.co.uk')])])])
if result != query_debug_result:
    print("Something in SOQL query result changed")
    print('SOQL query:', query_debug_result)
account_id = result['records'][0]['Id']
print('Account Id:', account_id)

client = sb.search("FIND {Pepper}")
print('SOSL search:', client)
# noinspection SpellCheckingInspection,LongLine
client_debug_result = OrderedDict([('searchRecords', [
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VDERUA4')])),
        ('Id', '00Q0O000010VDERUA4')]),
    OrderedDict([
         ('attributes', OrderedDict([('type', 'Lead'),
                                     ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VeygUAC')])),
         ('Id', '00Q0O000010VeygUAC')]),
    OrderedDict([
         ('attributes', OrderedDict([('type', 'Lead'),
                                     ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103AgRUAU')])),
         ('Id', '00Q0O0000103AgRUAU')]),
    OrderedDict([
         ('attributes', OrderedDict([('type', 'Lead'),
                                     ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000015iAeaUAE')])),
         ('Id', '00Q0O000015iAeaUAE')]),
    OrderedDict([
         ('attributes', OrderedDict([('type', 'Lead'),
                                     ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000144ulTUAQ')])),
         ('Id', '00Q0O0000144ulTUAQ')]),
    OrderedDict([
         ('attributes', OrderedDict([('type', 'Lead'),
                                     ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000012sl2PUAQ')])),
         ('Id', '00Q0O000012sl2PUAQ')]),
    OrderedDict([
         ('attributes', OrderedDict([('type', 'Lead'),
                                     ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010U2OnUAK')])),
         ('Id', '00Q0O000010U2OnUAK')]),
    OrderedDict([
         ('attributes', OrderedDict([('type', 'Lead'),
                                     ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010X0FyUAK')])),
         ('Id', '00Q0O000010X0FyUAK')]),
    OrderedDict([
         ('attributes', OrderedDict([('type', 'Lead'),
                                     ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103KMGUA2')])),
         ('Id', '00Q0O0000103KMGUA2')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000016Lk1dUAC')])),
        ('Id', '00Q0O000016Lk1dUAC')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010TbnQUAS')])),
        ('Id', '00Q0O000010TbnQUAS')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103v7HUAQ')])),
        ('Id', '00Q0O0000103v7HUAQ')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103wROUAY')])),
        ('Id', '00Q0O0000103wROUAY')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103uFjUAI')])),
        ('Id', '00Q0O0000103uFjUAI')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010TceyUAC')])),
        ('Id', '00Q0O000010TceyUAC')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103FUIUA2')])),
        ('Id', '00Q0O0000103FUIUA2')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102el0UAA')])),
        ('Id', '00Q0O0000102el0UAA')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000015iBc5UAE')])),
        ('Id', '00Q0O000015iBc5UAE')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UROyUAO')])),
        ('Id', '00Q0O000010UROyUAO')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103jGQUAY')])),
        ('Id', '00Q0O0000103jGQUAY')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000014vIAYUA2')])),
        ('Id', '00Q0O000014vIAYUA2')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UvQIUA0')])),
        ('Id', '00Q0O000010UvQIUA0')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UEPFUA4')])),
        ('Id', '00Q0O000010UEPFUA4')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VjyaUAC')])),
        ('Id', '00Q0O000010VjyaUAC')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010ViG0UAK')])),
        ('Id', '00Q0O000010ViG0UAK')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010ViroUAC')])),
        ('Id', '00Q0O000010ViroUAC')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VboHUAS')])),
        ('Id', '00Q0O000010VboHUAS')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010U1VxUAK')])),
        ('Id', '00Q0O000010U1VxUAK')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VIhOUAW')])),
        ('Id', '00Q0O000010VIhOUAW')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UjSgUAK')])),
        ('Id', '00Q0O000010UjSgUAK')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WZdIUAW')])),
        ('Id', '00Q0O000010WZdIUAW')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VUCrUAO')])),
        ('Id', '00Q0O000010VUCrUAO')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VR58UAG')])),
        ('Id', '00Q0O000010VR58UAG')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010381mUAA')])),
        ('Id', '00Q0O000010381mUAA')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000104NiYUAU')])),
        ('Id', '00Q0O0000104NiYUAU')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103dl0UAA')])),
        ('Id', '00Q0O0000103dl0UAA')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WaAKUA0')])),
        ('Id', '00Q0O000010WaAKUA0')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UdEdUAK')])),
        ('Id', '00Q0O000010UdEdUAK')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010491nUAA')])),
        ('Id', '00Q0O000010491nUAA')]),
    OrderedDict([
        ('attributes', OrderedDict([('type', 'Lead'),
                                    ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WRlQUAW')])),
        ('Id', '00Q0O000010WRlQUAW')]),
    OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103XRUUA2')])), ('Id', '00Q0O0000103XRUUA2')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VWiYUAW')])), ('Id', '00Q0O000010VWiYUAW')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UhHpUAK')])), ('Id', '00Q0O000010UhHpUAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010Vw0aUAC')])), ('Id', '00Q0O000010Vw0aUAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010W4YEUA0')])), ('Id', '00Q0O000010W4YEUA0')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UKknUAG')])), ('Id', '00Q0O000010UKknUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010W0O5UAK')])), ('Id', '00Q0O000010W0O5UAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UjB4UAK')])), ('Id', '00Q0O000010UjB4UAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UeF5UAK')])), ('Id', '00Q0O000010UeF5UAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010TlFFUA0')])), ('Id', '00Q0O000010TlFFUA0')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UXmGUAW')])), ('Id', '00Q0O000010UXmGUAW')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010W06lUAC')])), ('Id', '00Q0O000010W06lUAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010Vzu3UAC')])), ('Id', '00Q0O000010Vzu3UAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UrzLUAS')])), ('Id', '00Q0O000010UrzLUAS')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010XImUUAW')])), ('Id', '00Q0O000010XImUUAW')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WDIWUA4')])), ('Id', '00Q0O000010WDIWUA4')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WYrJUAW')])), ('Id', '00Q0O000010WYrJUAW')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WglwUAC')])), ('Id', '00Q0O000010WglwUAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WZ3SUAW')])), ('Id', '00Q0O000010WZ3SUAW')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WbARUA0')])), ('Id', '00Q0O000010WbARUA0')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UlF1UAK')])), ('Id', '00Q0O000010UlF1UAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103AtyUAE')])), ('Id', '00Q0O0000103AtyUAE')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WJgNUAW')])), ('Id', '00Q0O000010WJgNUAW')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WJgMUAW')])), ('Id', '00Q0O000010WJgMUAW')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WJa2UAG')])), ('Id', '00Q0O000010WJa2UAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WJa3UAG')])), ('Id', '00Q0O000010WJa3UAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010U6nLUAS')])), ('Id', '00Q0O000010U6nLUAS')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010XH7oUAG')])), ('Id', '00Q0O000010XH7oUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010XBTSUA4')])), ('Id', '00Q0O000010XBTSUA4')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010Vy0jUAC')])), ('Id', '00Q0O000010Vy0jUAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O00001031DqUAI')])), ('Id', '00Q0O00001031DqUAI')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UZBHUA4')])), ('Id', '00Q0O000010UZBHUA4')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VSkqUAG')])), ('Id', '00Q0O000010VSkqUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010Uo5sUAC')])), ('Id', '00Q0O000010Uo5sUAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VCGGUA4')])), ('Id', '00Q0O000010VCGGUA4')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UK0bUAG')])), ('Id', '00Q0O000010UK0bUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010W5FRUA0')])), ('Id', '00Q0O000010W5FRUA0')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010X6OTUA0')])), ('Id', '00Q0O000010X6OTUA0')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UcSZUA0')])), ('Id', '00Q0O000010UcSZUA0')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UDBtUAO')])), ('Id', '00Q0O000010UDBtUAO')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010XBcqUAG')])), ('Id', '00Q0O000010XBcqUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VuJIUA0')])), ('Id', '00Q0O000010VuJIUA0')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102fqKUAQ')])), ('Id', '00Q0O0000102fqKUAQ')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010V6WgUAK')])), ('Id', '00Q0O000010V6WgUAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WcEIUA0')])), ('Id', '00Q0O000010WcEIUA0')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UTBUUA4')])), ('Id', '00Q0O000010UTBUUA4')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WZKSUA4')])), ('Id', '00Q0O000010WZKSUA4')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VvzdUAC')])), ('Id', '00Q0O000010VvzdUAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WnAtUAK')])), ('Id', '00Q0O000010WnAtUAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WcqYUAS')])), ('Id', '00Q0O000010WcqYUAS')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WCLGUA4')])), ('Id', '00Q0O000010WCLGUA4')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WMShUAO')])), ('Id', '00Q0O000010WMShUAO')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WCXCUA4')])), ('Id', '00Q0O000010WCXCUA4')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010XGjdUAG')])), ('Id', '00Q0O000010XGjdUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VNgbUAG')])), ('Id', '00Q0O000010VNgbUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010U7lYUAS')])), ('Id', '00Q0O000010U7lYUAS')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VctiUAC')])), ('Id', '00Q0O000010VctiUAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102istUAA')])), ('Id', '00Q0O0000102istUAA')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VLXEUA4')])), ('Id', '00Q0O000010VLXEUA4')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103Hq8UAE')])), ('Id', '00Q0O0000103Hq8UAE')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102fqMUAQ')])), ('Id', '00Q0O0000102fqMUAQ')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102fqJUAQ')])), ('Id', '00Q0O0000102fqJUAQ')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102fqLUAQ')])), ('Id', '00Q0O0000102fqLUAQ')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102h5DUAQ')])), ('Id', '00Q0O0000102h5DUAQ')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102fHUUAY')])), ('Id', '00Q0O0000102fHUUAY')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O00001037OhUAI')])), ('Id', '00Q0O00001037OhUAI')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WZupUAG')])), ('Id', '00Q0O000010WZupUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O00001037UlUAI')])), ('Id', '00Q0O00001037UlUAI')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010TdGzUAK')])), ('Id', '00Q0O000010TdGzUAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102iU6UAI')])), ('Id', '00Q0O0000102iU6UAI')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010W9R9UAK')])), ('Id', '00Q0O000010W9R9UAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102iyrUAA')])), ('Id', '00Q0O0000102iyrUAA')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WZ2oUAG')])), ('Id', '00Q0O000010WZ2oUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102jlDUAQ')])), ('Id', '00Q0O0000102jlDUAQ')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WGEdUAO')])), ('Id', '00Q0O000010WGEdUAO')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O00001042DQUAY')])), ('Id', '00Q0O00001042DQUAY')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010W7U8UAK')])), ('Id', '00Q0O000010W7U8UAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WXyyUAG')])), ('Id', '00Q0O000010WXyyUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010V8ReUAK')])), ('Id', '00Q0O000010V8ReUAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WcGUUA0')])), ('Id', '00Q0O000010WcGUUA0')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WcXuUAK')])), ('Id', '00Q0O000010WcXuUAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VtPbUAK')])), ('Id', '00Q0O000010VtPbUAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VvJ8UAK')])), ('Id', '00Q0O000010VvJ8UAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VrvxUAC')])), ('Id', '00Q0O000010VrvxUAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102eu4UAA')])), ('Id', '00Q0O0000102eu4UAA')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010395HUAQ')])), ('Id', '00Q0O000010395HUAQ')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VIBvUAO')])), ('Id', '00Q0O000010VIBvUAO')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102gUjUAI')])), ('Id', '00Q0O0000102gUjUAI')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102h4cUAA')])), ('Id', '00Q0O0000102h4cUAA')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102gVuUAI')])), ('Id', '00Q0O0000102gVuUAI')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102gVtUAI')])), ('Id', '00Q0O0000102gVtUAI')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102iWzUAI')])), ('Id', '00Q0O0000102iWzUAI')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102idfUAA')])), ('Id', '00Q0O0000102idfUAA')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102hQzUAI')])), ('Id', '00Q0O0000102hQzUAI')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VJ3cUAG')])), ('Id', '00Q0O000010VJ3cUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000102ibGUAQ')])), ('Id', '00Q0O0000102ibGUAQ')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103LdpUAE')])), ('Id', '00Q0O0000103LdpUAE')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010TqwuUAC')])), ('Id', '00Q0O000010TqwuUAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VZALUA4')])), ('Id', '00Q0O000010VZALUA4')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010Van0UAC')])), ('Id', '00Q0O000010Van0UAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103EELUA2')])), ('Id', '00Q0O0000103EELUA2')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010U3KAUA0')])), ('Id', '00Q0O000010U3KAUA0')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010TkHkUAK')])), ('Id', '00Q0O000010TkHkUAK')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010Tk3mUAC')])), ('Id', '00Q0O000010Tk3mUAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010V0w2UAC')])), ('Id', '00Q0O000010V0w2UAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103LWZUA2')])), ('Id', '00Q0O0000103LWZUA2')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103olIUAQ')])), ('Id', '00Q0O0000103olIUAQ')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010491pUAA')])), ('Id', '00Q0O000010491pUAA')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010491oUAA')])), ('Id', '00Q0O000010491oUAA')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010VVSkUAO')])), ('Id', '00Q0O000010VVSkUAO')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103s73UAA')])), ('Id', '00Q0O0000103s73UAA')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O0000103Wg0UAE')])), ('Id', '00Q0O0000103Wg0UAE')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UpcKUAS')])), ('Id', '00Q0O000010UpcKUAS')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010UUe9UAG')])), ('Id', '00Q0O000010UUe9UAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WD0OUAW')])), ('Id', '00Q0O000010WD0OUAW')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WRFQUA4')])), ('Id', '00Q0O000010WRFQUA4')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WWtmUAG')])), ('Id', '00Q0O000010WWtmUAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010WYd6UAG')])), ('Id', '00Q0O000010WYd6UAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010W8v6UAC')])), ('Id', '00Q0O000010W8v6UAC')]), OrderedDict([('attributes', OrderedDict([('type', 'Lead'), ('url', '/services/data/v38.0/sobjects/Lead/00Q0O000010W3NFUA0')])), ('Id', '00Q0O000010W3NFUA0')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000255YqjQAE')])), ('Id', '0030O0000255YqjQAE')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256XL0QAM')])), ('Id', '0030O0000256XL0QAM')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256YZOQA2')])), ('Id', '0030O0000256YZOQA2')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256K5YQAU')])), ('Id', '0030O0000256K5YQAU')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256LKFQA2')])), ('Id', '0030O0000256LKFQA2')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256BCmQAM')])), ('Id', '0030O0000256BCmQAM')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256BLCQA2')])), ('Id', '0030O0000256BLCQA2')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256ArpQAE')])), ('Id', '0030O0000256ArpQAE')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256B94QAE')])), ('Id', '0030O0000256B94QAE')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256AyfQAE')])), ('Id', '0030O0000256AyfQAE')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256BL5QAM')])), ('Id', '0030O0000256BL5QAM')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256BHTQA2')])), ('Id', '0030O0000256BHTQA2')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256B7xQAE')])), ('Id', '0030O0000256B7xQAE')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O00002LHPRHQA5')])), ('Id', '0030O00002LHPRHQA5')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256TqLQAU')])), ('Id', '0030O0000256TqLQAU')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256HRdQAM')])), ('Id', '0030O0000256HRdQAM')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256EuOQAU')])), ('Id', '0030O0000256EuOQAU')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O0000256DFlQAM')])), ('Id', '0030O0000256DFlQAM')]), OrderedDict([('attributes', OrderedDict([('type', 'Contact'), ('url', '/services/data/v38.0/sobjects/Contact/0030O00002LHNmMQAX')])), ('Id', '0030O00002LHNmMQAX')]), OrderedDict([('attributes', OrderedDict([('type', 'Account'), ('url', '/services/data/v38.0/sobjects/Account/0010O00001sKYf9QAG')])), ('Id', '0010O00001sKYf9QAG')]), OrderedDict([('attributes', OrderedDict([('type', 'Account'), ('url', '/services/data/v38.0/sobjects/Account/0010O000022XeoAQAS')])), ('Id', '0010O000022XeoAQAS')]), OrderedDict([('attributes', OrderedDict([('type', 'Account'), ('url', '/services/data/v38.0/sobjects/Account/0010O000022XdbOQAS')])), ('Id', '0010O000022XdbOQAS')]), OrderedDict([('attributes', OrderedDict([('type', 'Survey__c'), ('url', '/services/data/v38.0/sobjects/Survey__c/a8x0O000000XfSDQA0')])), ('Id', 'a8x0O000000XfSDQA0')])])])

if client != client_debug_result:
    print("Something in SOSL search result changed")
    print('SOSL search:', client_debug_result)

count_client_types = dict()
for cl in client['searchRecords']:
    ct = cl['attributes']['type']
    if ct in count_client_types:
        count_client_types[ct] += 1
    else:
        count_client_types[ct] = 1

    client_id = cl['Id']
    if client_id == account_id:
        print("Account object of Pepper also found in SOSL result:", cl)
print("client type counts:", count_client_types)

a_data = sb.Account.get(account_id)
print('Account data:', a_data)

c_with_rci = sb.search("FIND {1234\-56789}")
print('SOSL ext refs custom object search for RCI ref:', c_with_rci)

c_with_acu = sb.search("FIND {E624857}")
print('SOSL custom field search for Acumen ref E624857:', c_with_acu)

c_data2 = sb.Contact.get_by_custom_id('AcumenClientRef__c', 'E624857')
print('Contact data by Acumen ref. custom field:', c_data2)

# ERROR 12/2018:
# {'message': 'Provided external ID field does not exist or is not accessible:
# .. AcumenClientRef__pc', 'errorCode': 'NOT_FOUND'}
# a_data2 = sb.Account.get_by_custom_id('AcumenClientRef__pc', 'E624857')
# print('Account data by Acumen ref. custom field:', a_data2)

# the RCI_Reference__c custom field is NOT an External ID
try:
    c_data2 = sb.Contact.get_by_custom_id('RCI_Reference__c', '9876\-54321')
except SalesforceResourceNotFound as ex:
    print('  ****  RCI_Reference__c custom field is not an External Id  ****  ', ex)
else:
    print('Contact data fetched via RCI ref. custom field:', c_data2)

try:
    c_data3 = sb.External_Ref__c.get(account_id)
except SalesforceResourceNotFound as ex:
    print('  ****  Reference_Ref__c custom object is not fetch-able  ****  ', ex)
else:
    print("External Ref data fetched via client_id", c_data3)

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

result = sb.query_all("SELECT Id FROM External_Ref__c WHERE Reference_No_or_ID__c = 'abc-efg'")
print('SOQL exact query Test123:', result)

ext_ref = sb.search("FIND {1234\-5678*}")
print('SOSL like ext ref search:', ext_ref)

ext_ref = sb.search("FIND {1234*}")
print('SOSL like ext ref search:', ext_ref)

ext_ref = sb.search("FIND {RCI_1}")
print('SOSL exact ext ref name search:', ext_ref)

ext_ref = sb.search("FIND {1234\-56789}")
print('SOSL exact ext ref search:', ext_ref)

ext_ref = sb.search("FIND {RCI}")
print('SOSL exact ext ref type search:', ext_ref)

ext_ref_id = [_['Id'] for _ in ext_ref['searchRecords'] if _['attributes']['type'] == 'External_Ref__c'][0]
ext_ref_data = sb.External_Ref__c.get(ext_ref_id)
print('Ext Ref Data:', ext_ref_data)

ext_ref_client = ext_ref_data['Contact__c']
if ext_ref_client:
    client_data = sb.Contact.get(ext_ref_client)
    obj_type = 'Contact'
else:
    ext_ref_client = ext_ref_data['Account__c']
    client_data = sb.Account.get(ext_ref_client)
    obj_type = 'Account'
print(obj_type, 'data fetched via RCI ref:', client_data)

result = sb.query_all("SELECT Id FROM External_Ref__c WHERE {}__c = '{}'".format(obj_type, ext_ref_client))
print(obj_type, 'SOQL query fetching all external ref IDs from Pepper:', result)

records = result['records']  # list of OrderedDict with Id item/key
rec_ids = [_['Id'] for _ in records]
print(obj_type, 'Ext Ref Ids of last SOQL query:', rec_ids)

result = sb.query_all("SELECT Reference_No_or_ID__c FROM External_Ref__c WHERE {}__c = '{}'"
                      .format(obj_type, ext_ref_client))
print(obj_type, 'SOQL query fetching all external ref numbers from Pepper:', result)
records = result['records']  # list of OrderedDict with external ref no
rec_nos = [_['Reference_No_or_ID__c'] for _ in records]
print(obj_type, 'Ext Ref numbers of last SOQL query:', rec_nos)

new_no = '1234-8902'
if new_no in rec_nos:
    print("  ####  External ref no", new_no, "already created in", obj_type, "for Pepper with ID", ext_ref_client)
else:
    ret = sb.External_Ref__c.create({obj_type + '__c': ext_ref_client, 'Reference_No_or_ID__c': new_no,
                                     # 'Type__c': 'RCI',
                                     'Name': 'RCI_9'})
    print(obj_type, 'Created Ext Ref return1:', ret)

new_no = 'abc-7890'
test_contact_id = '0039E00000Dla2VQAR'  # (test_contact_id in clients) fails with 15 character ID == '0039E00000Dla2V'
# noinspection SpellCheckingInspection
test_account_id = '0011q00000CswsTAAR'
result = sb.query_all("SELECT Id, Contact__c, Account__c FROM External_Ref__c WHERE Reference_No_or_ID__c = '{}'"
                      .format(new_no))
print('SOQL querying RCI ref number from Test:', result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] for _ in records]
    print('Ext Ref Ids of last SOQL query:', ids)
    clients = [_[obj_type + '__c'] for _ in records]
    print('Ext Ref Contact/Account Ids of last SOQL query:', clients)
    if test_contact_id in clients:
        print('  ####  External RCI ref number', new_no, 'already exists for Test contact with ID', test_contact_id)
    elif test_account_id in clients:
        print('  ####  External RCI ref number', new_no, 'already exists for Test account with ID', test_account_id)
    else:
        ret = sb.External_Ref__c.create({obj_type + '__c': test_contact_id, 'Reference_No_or_ID__c': new_no,
                                         # 'Type__c': 'RCI',
                                         'Name': 'RCI_88'})
        print('    Created Ext Ref return2 for Test:', ret)
        if ret['success']:
            ret = sb.External_Ref__c.upsert(ret['id'],
                                            {'Name': 'RCI_8'})
            print('        Upsert Ext Ref return3 for Test(changed RCI_88 to RCI_8):', ret)


elif result['done']:
    print('  ####  last SOQL query done but no records found, totalSize=', result['totalSize'])
else:
    print('  ****  last SOQL query failed to be executed/done completely')

result = sb.query_all("SELECT Id FROM {} WHERE RCI_Reference__{}c = '{}'"
                      .format(obj_type, 'p' if obj_type == 'Account' else '', 'abc-9876'))
print(obj_type, 'SOQL querying main RCI ref number (abc-9876) from Test:', result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] for _ in records]
    print('    Ext Ref Ids of last SOQL query:', ids)

result = sb.query_all("SELECT {}__c, Id FROM External_Ref__c WHERE Name LIKE '{}'".format(obj_type, 'RCI%'))
print("SOQL querying", obj_type, "Ids with external RCI Ids", result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    clients = [str(_.get(obj_type + '__c')) + '=' + _['Id'] for _ in records]
    print("    Ext Ref", obj_type, "Ids with RCI Id of last SOQL query:", clients)

result = sb.query_all("SELECT {}__c FROM External_Ref__c WHERE Name LIKE 'RCI%' GROUP BY {}__c"
                      .format(obj_type, obj_type))
print("SOQL querying distinct", obj_type, "Ids with external RCI Ids", result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    clients = [_.get(obj_type + '__c') for _ in records]
    print("    Ext Ref", obj_type, "Ids of last SOQL query:", clients)

result = sb.query_all("SELECT Id FROM Contact WHERE RCI_Reference__c != NULL")
print("SOQL querying Contact Ids with main RCI Ids", result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] for _ in records]
    print("    Contact Ids with main RCI Refs of last SOQL query:", ids)

result = sb.query_all("SELECT Id FROM Account WHERE RCI_Reference__pc != NULL")
print("SOQL querying Account Ids with main RCI Ids", result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] for _ in records]
    print("    Account Ids with main RCI Refs of last SOQL query:", ids)

# next query results in error: Semi join sub-selects are not allowed with the 'OR' operator
# result = sb.query_all("SELECT Id, AcumenClientRef__c, RCI_Reference__c FROM Contact WHERE RCI_Reference__c != NULL"
#                      " or Id in (SELECT Contact__c FROM External_Ref__c WHERE Name LIKE 'RCI%')")
# .. do using different approach:
result = sb.query_all("SELECT Id, AcumenClientRef__c, RCI_Reference__c,"
                      " (SELECT Reference_No_or_ID__c, Name FROM External_References__r)"
                      " FROM Contact"
                      " WHERE RCI_Reference__c != NULL")
print('SOQL querying Contact data with main or external RCI Ids', result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] + '=' + e['Reference_No_or_ID__c'] for _ in records if _['External_References__r']
           for e in _['External_References__r']['records']]
    print('    Ext Ref Ids of last SOQL query:', ids)

# .. same as above restricted to external RCI refs
# .. and without duplicates (but SF doesn't support GROUP BY Reference_No_or_ID__c in sub-query)
result = sb.query_all("SELECT Id, AcumenClientRef__c, RCI_Reference__c,"
                      " (SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%')"
                      " FROM Contact"
                      " WHERE RCI_Reference__c != NULL"
                      # SF doesn't allow sub-queries in WHERE clause
                      # " or (SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%') != NULL")
                      )
print('SOQL querying Contact data with unique main or external RCI Ids', result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] + '=' + e['Reference_No_or_ID__c'] for _ in records if _['External_References__r']
           for e in _['External_References__r']['records']]
    print('    Ext Ref Ids of unique Contact-related SOQL query:', ids)


# .. same as above but for Account
result = sb.query_all("SELECT Id, AcumenClientRef__pc, RCI_Reference__pc"
                      ", (SELECT Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%')"
                      ", (SELECT Reference_No_or_ID__c FROM External_References__pr WHERE Name LIKE 'RCI%')"
                      " FROM Account"
                      " WHERE RCI_Reference__pc != NULL"
                      )
print('SOQL querying Account data with unique main or external RCI Ids', result)
if result['done'] and result['totalSize'] > 0:
    records = result['records']  # list of OrderedDict with external ref no
    ids = [_['Id'] + '=' + e['Reference_No_or_ID__c'] for _ in records if _['External_References__r']
           for e in _['External_References__r']['records']]
    print('    Ext Ref Ids of unique Contact/Account-related SOQL query:', ids)
    ids = [_['Id'] + '=' + e['Reference_No_or_ID__c'] for _ in records if _['External_References__pr']
           for e in _['External_References__pr']['records']]
    print('    Ext Ref Ids of unique PersonAccount-related SOQL query:', ids)


# SOQL query to include record type of Contact
result = sb.query_all("SELECT Id, Name, RecordType.DeveloperName FROM Contact WHERE LastName = 'Pepper'")
if result['done'] and result['totalSize'] > 0:
    records = result['records']
    print("   first record", records[0], " number of records", len(records))
    rec_type = records[0]['RecordType']
    print("Fetch client data with RecordType", rec_type, "DeveloperName", rec_type['DeveloperName'] if rec_type else "")

# check create/update/delete of Contact object
result = sb.query_all("Select Id From RecordType Where SobjectType = 'Contact' and DeveloperName = 'Rentals'")
if result['done'] and result['totalSize'] > 0:
    rec_type = result['records'][0]['Id']
    # noinspection SpellCheckingInspection
    print("RecordTypeId=", rec_type)    # == '0129E000000CmLVQA0', LATER=='0120O000000dN6YQAU'
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


# SOQL query to include record type of Account
result = sb.query_all("SELECT Id, Name, RecordType.DeveloperName FROM Account WHERE LastName = 'Pepper'")
if result['done'] and result['totalSize'] > 0:
    records = result['records']
    print("   first record", records[0], " number of records", len(records))
    rec_type = records[0]['RecordType']
    print("Fetch client data with RecordType", rec_type, "DeveloperName", rec_type['DeveloperName'] if rec_type else "")

# check create/update/delete of Account object
result = sb.query_all("Select Id From RecordType Where SobjectType = 'Account' and DeveloperName = 'Rentals'")
if result['done'] and result['totalSize'] > 0:
    rec_type = result['records'][0]['Id']
    print("RecordTypeId=", rec_type)    # ==
    email = 'y_u_h_u@yahoo.com'
    sb.error_message = ''
    result = sb.query_all("SELECT Id FROM Account WHERE PersonEmail = '" + email + "'")
    if result['done']:
        if result['totalSize'] > 0:
            print(".. updating")
            sb.Contact.update(result['records'][0]['Id'],
                              {'FirstName': 'Sally', 'LastName': 'S-force', 'RecordTypeId': rec_type,
                               'PersonEmail': email, 'Birthdate': '1952-6-18', 'Description': None})
        else:
            print(".. inserting")
            sb.Contact.create({'FirstName': 'Sally', 'LastName': 'S-force', 'RecordTypeId': rec_type,
                               'PersonEmail': email, 'Birthdate': '1962-6-18'})
        if sb.error_message:
            print("Salesforce error:", sb.error_message)

# extract data for to double check phone validation done with data-8 against the byteplant phone validator
result = sb.query_all("SELECT Id, Country__pc, PersonHomePhone, PersonMobilePhone, Work_Phone__pc,"
                      " CD_Htel_valid__pc, CD_mtel_valid__pc, CD_wtel_valid__pc"
                      " FROM Account"
                      " WHERE CD_Htel_valid__pc != NULL or CD_mtel_valid__pc != NULL or CD_wtel_valid__pc != NULL")
if result['done'] and result['totalSize'] > 0:
    records = result['records']
    for rec in records:
        print(rec['Id'], rec['Country__pc'],
              rec['PersonHomePhone'], rec['CD_Htel_valid__pc'], rec['PersonMobilePhone'], rec['CD_mtel_valid__pc'],
              rec['Work_Phone__pc'], rec['CD_wtel_valid__pc'])


# using APEX REST service - NO LONGER IMPLEMENTED
# params = dict(email="test@test.test", phone="0034922777888", firstName="Testy", lastName="Tester")
# result = sb.apexecute('clientsearch', method='POST', data=params)
# print('APEX REST call result', result)


# noinspection SpellCheckingInspection
'''
BACKUP of working SOQL queries (from Developer Console):

SELECT Id, Name, (select Contact.Name from Account.Contacts) C 
  FROM Account
 WHERE Id IN (select ConvertedAccountId from Lead where Id = '00Q0O000010Rfb2UAC')

SELECT Id, Name, 
       (select Contact.Id, Contact.Name from Account.Contacts), 
       (select Lead.Id, Lead.Name from Account.Leads__r)
  FROM Account where Id = '0010O00001sm5pyQAA'

SELECT Id, Name, Reference_No_or_ID__c, Contact__c, Account__c 
  FROM External_Ref__c

SELECT id, Name, 
       (SELECT Name, Reference_No_or_ID__c FROM External_References__r WHERE Name LIKE 'RCI%') 
  FROM Account

select Id, RecordTypeId, RecordType.DeveloperName 
  FROM Opportunity where RecordType.DeveloperName in ('Sihot_Generated', 'Service_Center_Booking')

SELECT Id, AccountId, Name, Resort__c, Room_Number__c, REQ_Acm_Arrival_Date__c, REQ_Acm_Departure_Date__c, 
       RecordType.name
  FROM Opportunity where resort__c != null

SELECT Id, 
       (SELECT CreatedDate, HotelId__c, Number__c, SubNumber__c, GdsNo__c, Arrival__c, Departure__c, Status__c, 
               RoomNo__c, MktSegment__c, MktGroup__c, RoomCat__c, Adults__c, Children__c, Note__c, SihotResvObjectId__c 
          FROM Reservations__r) 
  FROM Opportunity, Opportunity.Account 
 WHERE Opportunity.Account.Id = '0010O00001sKdq1QAC'

SELECT Id, 
       (SELECT Id, CreatedDate, HotelId__c, Number__c, SubNumber__c, GdsNo__c, Arrival__c, Departure__c, Status__c, 
               RoomNo__c, MktSegment__c, MktGroup__c, RoomCat__c, Adults__c, Children__c, Note__c, SihotResvObjectId__c
          FROM Reservations__r) 
  FROM Opportunity WHERE Id = '006...'

SELECT Id, 
       (SELECT Id, CheckIn__c, CheckOut__c, RoomNumbers__c from Allocations__r), 
       CreatedDate, HotelId__c, Number__c, 
       SubNumber__c, GdsNo__c, Arrival__c, Departure__c, Status__c, RoomNo__c, MktSegment__c, MktGroup__c, 
       RoomCat__c, Adults__c, Children__c, Note__c, SihotResvObjectId__c 
  FROM Reservation__c WHERE Id = 'a8G0O000000YEstUAG'

SELECT id, number__c, 
       (select id from Allocations__r) 
  FROM Reservation__c where id = 'a8G0O000000YXBtUAO'

SELECT Account__r.Id, Account__r.PersonEmail, Account__r.PersonHomePhone, Account__r.Language__pc,
       Opportunity__c,
       Id,
       HotelId__c, Number__c, SubNumber__c, 
       GdsNo__c, Arrival__c, Departure__c, Status__c,
       Adults__c,
       (SELECT Id, CheckIn__c from Allocations__r) 
  FROM Reservation__c 
 WHERE HotelId__c = '3'
   AND Arrival__c = 2018-09-21
   AND Adults__c = 2
   AND Account__r.FirstName LIKE 'John%'

SELECT Account__r.Id, Account__r.Name, Account__r.PersonEmail, Account__r.PersonHomePhone, Account__r.Language__pc,
       Opportunity__c,
       Id,
       HotelId__c, Number__c, SubNumber__c, 
       (SELECT CheckIn__c from Allocations__r WHERE CheckIn__c >= 2019-09-21T00:03:54.000+0000)
  FROM Reservation__c 
 WHERE HotelId__c = '3'
   AND Arrival__c = 2018-09-21
   AND Adults__c >= 2
   AND Account__r.FirstName LIKE 'John%'

SELECT Account__r.Id, 
       Id, 
       Reservation__r.id, Reservation__r.number__c
  FROM Allocation__c
 WHERE Account__r.Id != null and Reservation__r.Id != null
 
SELECT Id, CheckIn__c,
       Reservation__r.id, Reservation__r.number__c, Reservation__r.Arrival__c,
       Reservation__r.Opportunity__c, Reservation__r.Opportunity__r.RecordTypeId,
       Reservation__r.Account__c,
       Account__r.Id
  FROM Allocation__c
 WHERE Account__r.Id != null and Reservation__r.Id != null and Reservation__r.Opportunity__c != null

SELECT Account__r.Id, 
       Account__r.AcumenClientRef__pc 
       Account__r.SihotGuestObjId__pc, 
       Account__r.FirstName, Account__r.LastName, Account__r.PersonEmail, Account__r.PersonHomePhone,
       Account__r.Language__pc, 
       Account__r.PersonMailingStreet, Account__r.PersonMailingPostalCode, Account__r.PersonMailingCity, 
       Account__r.PersonMailingCountry, 
       Account__r.CurrencyIsoCode, Account__r.Nationality__pc, 
       Reservation__r.Opportunity__c,
       Reservation__r.Id,
       Reservation__r.HotelId__c, Reservation__r.Number__c, Reservation__r.SubNumber__c, 
       Reservation__r.GdsNo__c, Reservation__r.Arrival__c, Reservation__r.Departure__c, Reservation__r.Status__c,  
       Reservation__r.RoomNo__c, Reservation__r.MktSegment__c, Reservation__r.MktGroup__c, Reservation__r.RoomCat__c, 
       Reservation__r.Adults__c, Reservation__r.Children__c, Reservation__r.Note__c, 
       Reservation__r.SihotResvObjectId__c,
       CheckIn__c
  FROM Allocation__c 
 WHERE Id = 'a9H0O000000XhejUAC'

SELECT Account__r.Id, Account__r.PersonEmail, Account__r.PersonHomePhone, Account__r.Language__pc,
       Reservation__r.Opportunity__c,
       Reservation__r.Id,
       Reservation__r.HotelId__c, Reservation__r.Number__c, Reservation__r.SubNumber__c, 
       Reservation__r.GdsNo__c, Reservation__r.Arrival__c, Reservation__r.Departure__c, Reservation__r.Status__c,
       Reservation__r.Adults__c,  
       CheckIn__c
  FROM Allocation__c 
 WHERE CheckIn__c = 2018-09-28T08:19:54.000+0000
   AND Reservation__r.HotelId__c = '3'
   AND Reservation__r.Arrival__c = 2018-09-21
   AND Reservation__r.Adults__c = 2
   AND Account__r.FirstName LIKE 'John%'

Detect Opportunities with more than one reservation associated (LIMIT not needed in full sandbox)

SELECT Opportunity__c, COUNT(Id)
  FROM Reservation__c
WHERE Opportunity__r.RecordType.Name like 'Sihot%'
GROUP BY Opportunity__c
HAVING COUNT(Id) > 1
ORDER BY COUNT(Id) desc
LIMIT 1000

'''
