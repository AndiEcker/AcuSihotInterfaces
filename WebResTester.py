from ae_console_app import ConsoleApp, Progress, uprint, DEBUG_LEVEL_VERBOSE
from sxmlif import SihotXmlBuilder, ResToSihot, SXML_DEF_ENCODING
from acif import add_ac_options
from shif import add_sh_options

__version__ = '0.1'

cae = ConsoleApp(__version__, "Test SIHOT WEB.PMS interface", debug_level_def=DEBUG_LEVEL_VERBOSE,
                 additional_cfg_files=['SihotMktSegExceptions.cfg'])
add_ac_options(cae)
add_sh_options(cae, add_kernel_port=True)

# select reservation by gdsNo (priority) or client ref/matchcode and if both is empty then send file WebResTester.req
cae.add_option('gdsNo', 'Send reservations of the reservation identified with this GDSNO/RU_CODE', '')  # 1098704')
cae.add_option('client', 'Send reservations of the client identified with this matchcode', '')  # Z008475')  # N617081')
# E362344')  # C605765')


uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), cae.get_option('acuDSN'))
uprint('Server IP/Web-/Kernel-port:', cae.get_option('shServerIP'), cae.get_option('shServerPort'),
       cae.get_option('shServerKernelPort'))
uprint('TCP Timeout/XML Encoding:', cae.get_option('shTimeout'), cae.get_option('shXmlEncoding'))

err_msg = ''
client_code = cae.get_option('client')
gds_no = cae.get_option('gdsNo')
if client_code or gds_no:
    if gds_no:
        client_msg = ' of reservation GDSNO {gdsNo} to Sihot'.format(gdsNo=gds_no)
    else:
        client_msg = ' of client {client} to Sihot'.format(client=client_code)

    uprint('####  Fetching client res  ####')

    acumen_req = ResToSihot(cae, use_kernel_interface=False)
    err_msg = acumen_req.fetch_from_acu_by_aru("RU_CODE = " + gds_no if gds_no else "CD_CODE = '" + client_code + "'")
    if not err_msg and not acumen_req.row_count:
        if gds_no:
            err_msg = acumen_req.fetch_all_valid_from_acu(where_group_order="RU_CODE = " + gds_no)
        else:
            err_msg = acumen_req.fetch_from_acu_by_cd(client_code)      # UNFILTERED !!! (possibly inactive hotel)
    progress = Progress(cae.get_option('debugLevel'), start_counter=acumen_req.row_count,
                        start_msg='####  Prepare sending of {total_count} reservation requests' + client_msg,
                        nothing_to_do_msg='****  SihotMigration: acumen_req fetch returning no rows')

    for crow in acumen_req.rows:
        err_msg = acumen_req.send_row_to_sihot(crow, commit=True)
        progress.next(processed_id=str(crow['RUL_PRIMARY']) + '/' + str(crow['RUL_CODE']), error_msg=err_msg)

    progress.finished(error_msg=err_msg)

else:
    uprint('####  Preparing XML .....  ####')

    with open('test/WebResTester.req', 'r') as f:
        xml = f.read()

    sxb = SihotXmlBuilder(cae, use_kernel_interface=False, elem_col_map=(), connect_to_acu=False)
    sxb.xml = xml

    uprint('####  Sending ...........  ####')

    err_msg = sxb.send_to_server()

    uprint('####  Response ..........  ####')

    uprint(err_msg)

    uprint('####  Finished ..........  ####')
