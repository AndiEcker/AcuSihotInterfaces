from ae_console_app import ConsoleApp, Progress, uprint, DEBUG_LEVEL_VERBOSE
from sxmlif import SihotXmlBuilder, AcuClientToSihot, SXML_DEF_ENCODING
from acif import add_ac_options
from shif import add_sh_options

__version__ = '0.1'

cae = ConsoleApp(__version__, "Test SIHOT Kernel guest interface", debug_level_def=DEBUG_LEVEL_VERBOSE)
add_sh_options(cae, add_kernel_port=True)

add_ac_options(cae)

cae.add_option('client', 'Send unsynced client identified with this matchcode', '')  # C605765')


uprint('Server IP/Web-/Kernel-port:', cae.get_option('shServerIP'), cae.get_option('shServerKernelPort'))
uprint('TCP Timeout/XML Encoding:', cae.get_option('shTimeout'), cae.get_option('shXmlEncoding'))

err_msg = ''
client_code = cae.get_option('client')
if client_code:
    client_msg = ' of client {client} to Sihot'.format(client=client_code)

    uprint('####  Fetching client res  ####')

    acumen_client = AcuClientToSihot(cae)
    err_msg = acumen_client.fetch_from_acu_by_acu(client_code)
    if not err_msg and not acumen_client.row_count:
        err_msg = acumen_client.fetch_from_acu_by_cd(client_code)
    progress = Progress(cae.get_option('debugLevel'), start_counter=acumen_client.row_count,
                        start_msg='Prepare sending of {total_count} reservation requests' + client_msg,
                        nothing_to_do_msg='SihotMigration: acumen_req fetch returning no rows')

    uprint('####  Sending ...........  ####')

    for crow in acumen_client.rows:
        err_msg = acumen_client.send_client_to_sihot(crow, commit=True)
        progress.next(processed_id=str(crow['CD_CODE']) + '/' + str(crow['CDL_CODE']), error_msg=err_msg)

    progress.finished(error_msg=err_msg)

else:
    uprint('####  Preparing XML .....  ####')

    with open('test/KernelGuestTester.req', 'r') as f:
        xml = f.read()

    uprint(xml)

    uprint('####  Sending ...........  ####')

    sxb = SihotXmlBuilder(cae, use_kernel=True, elem_col_map=(), connect_to_acu=False)
    sxb.xml = xml
    err_msg = sxb.send_to_server()

    uprint('####  Response ..........  ####')

    uprint(err_msg)

    uprint('####  Finished ..........  ####')
