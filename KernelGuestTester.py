from sys_data_ids import DEBUG_LEVEL_VERBOSE, SDF_SH_KERNEL_PORT, SDF_SH_TIMEOUT, SDF_SH_XML_ENCODING
from ae.console_app import ConsoleApp, Progress, uprint
from sxmlif import SihotXmlBuilder
from acif import add_ac_options, AcuClientToSihot
from shif import add_sh_options

__version__ = '0.1'

cae = ConsoleApp(__version__, "Test SIHOT Kernel guest interface", debug_level_def=DEBUG_LEVEL_VERBOSE)
add_sh_options(cae, add_kernel_port=True)

add_ac_options(cae)

cae.add_option('client', 'Send unsynced client identified with this matchcode', '')  # C605765')


uprint('Server IP/Web-/Kernel-port:', cae.get_option('shServerIP'), cae.get_option(SDF_SH_KERNEL_PORT))
uprint('TCP Timeout/XML Encoding:', cae.get_option(SDF_SH_TIMEOUT), cae.get_option(SDF_SH_XML_ENCODING))

err_msg = ''
client_code = cae.get_option('client')
if client_code:
    client_msg = ' of client {client} to Sihot'.format(client=client_code)

    uprint('####  Fetching client res  ####')

    acumen_client = AcuClientToSihot(cae)
    err_msg = acumen_client.fetch_from_acu_by_acu(client_code)
    if not err_msg and not len(acumen_client.recs):
        err_msg = acumen_client.fetch_from_acu_by_cd(client_code)
    progress = Progress(cae, start_counter=len(acumen_client.recs),
                        start_msg=' ###  Prepare sending of {total_count} reservation requests' + client_msg,
                        nothing_to_do_msg='SihotMigration: acumen_client fetch returning no recs')

    uprint('####  Sending ...........  ####')

    for rec in acumen_client.recs:
        err_msg = acumen_client.send_client_to_sihot(rec)
        progress.next(processed_id=str(rec['AcuId']) + '/' + str(rec['AcuLogId']), error_msg=err_msg)

    progress.finished(error_msg=err_msg)

else:
    uprint('####  Preparing XML .....  ####')

    with open('test/KernelGuestTester.req') as f:
        xml = f.read()

    uprint(xml)

    uprint('####  Sending ...........  ####')

    sxb = SihotXmlBuilder(cae, use_kernel=True)
    sxb.xml = xml
    err_msg = sxb.send_to_server()

    uprint('####  Response ..........  ####')

    uprint(err_msg)

    uprint('####  Finished ..........  ####')
