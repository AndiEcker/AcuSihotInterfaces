from ae_console_app import ConsoleApp, Progress, uprint, DEBUG_LEVEL_VERBOSE
from ae_db import DEF_USER, DEF_DSN
from sxmlif import SihotXmlBuilder, ClientToSihot, SXML_DEF_ENCODING

__version__ = '0.1'

cae = ConsoleApp(__version__, "Test SIHOT Kernel guest interface", debug_level_def=DEBUG_LEVEL_VERBOSE)
cae.add_option('serverIP', "IP address of the SIHOT interface server", 'localhost', 'i')
cae.add_option('serverKernelPort', "IP port of the KERNEL interface of this server", 14772, 'k')

cae.add_option('timeout', "Timeout value for TCP/IP connections", 39.6)
cae.add_option('xmlEncoding', "Charset used for the xml data", SXML_DEF_ENCODING, 'e')

cae.add_option('acuUser', "User name of Acumen/Oracle system", DEF_USER, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", DEF_DSN, 'd')

cae.add_option('client', 'Send unsynced client identified with this matchcode', '')  # C605765')


uprint('Server IP/Web-/Kernel-port:', cae.get_option('serverIP'), cae.get_option('serverKernelPort'))
uprint('TCP Timeout/XML Encoding:', cae.get_option('timeout'), cae.get_option('xmlEncoding'))

err_msg = ''
client_code = cae.get_option('client')
if client_code:
    client_msg = ' of client {client} to Sihot'.format(client=client_code)

    uprint('####  Fetching client res  ####')

    acumen_client = ClientToSihot(cae, use_kernel_interface=True)
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

    sxb = SihotXmlBuilder(cae, use_kernel_interface=True, col_map=(), connect_to_acu=False)
    sxb.xml = xml
    err_msg = sxb.send_to_server()

    uprint('####  Response ..........  ####')

    uprint(err_msg)

    uprint('####  Finished ..........  ####')
