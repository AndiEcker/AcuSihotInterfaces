from ae.core import DEBUG_LEVEL_VERBOSE
from ae.console import ConsoleApp
from ae.progress import Progress
from ae.sys_core_sh import \
    SihotXmlBuilder, SDF_SH_KERNEL_PORT, SDF_SH_SERVER_ADDRESS, SDF_SH_TIMEOUT, SDF_SH_XML_ENCODING
from sys_data_acu import add_ac_options, AcuClientToSihot
from ae.sys_data_sh import add_sh_options

__version__ = '0.1'

cae = ConsoleApp("Test SIHOT Kernel guest interface", debug_level=DEBUG_LEVEL_VERBOSE)
add_sh_options(cae, add_kernel_port=True)

add_ac_options(cae)

cae.add_opt('client', 'Send unsynced client identified with this matchcode', '')  # C605765')


cae.po('Server IP/Web-/Kernel-port:', cae.get_opt(SDF_SH_SERVER_ADDRESS), cae.get_opt(SDF_SH_KERNEL_PORT))
cae.po('TCP Timeout/XML Encoding:', cae.get_opt(SDF_SH_TIMEOUT), cae.get_opt(SDF_SH_XML_ENCODING))

err_msg = ''
client_code = cae.get_opt('client')
if client_code:
    client_msg = ' of client {client} to Sihot'.format(client=client_code)

    cae.po('####  Fetching client res  ####')

    acumen_client = AcuClientToSihot(cae)
    err_msg = acumen_client.fetch_from_acu_by_acu(client_code)
    if not err_msg and not len(acumen_client.recs):
        err_msg = acumen_client.fetch_from_acu_by_cd(client_code)
    progress = Progress(cae, start_counter=len(acumen_client.recs),
                        start_msg=' ###  Prepare sending of {total_count} reservation requests' + client_msg,
                        nothing_to_do_msg='SihotMigration: acumen_client fetch returning no recs')

    cae.po('####  Sending ...........  ####')

    for rec in acumen_client.recs:
        err_msg = acumen_client.send_client_to_sihot(rec)
        progress.next(processed_id=str(rec['AcuId']) + '/' + str(rec['AcuLogId']), error_msg=err_msg)

    progress.finished(error_msg=err_msg)

else:
    cae.po('####  Preparing XML .....  ####')

    with open('test/KernelGuestTester.req') as f:
        xml = f.read()

    cae.po(xml)

    cae.po('####  Sending ...........  ####')

    sxb = SihotXmlBuilder(cae, use_kernel=True)
    sxb.xml = xml
    err_msg = sxb.send_to_server()

    cae.po('####  Response ..........  ####')

    cae.po(err_msg)

    cae.po('####  Finished ..........  ####')
