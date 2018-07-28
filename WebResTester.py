import os
from ae_console_app import ConsoleApp, Progress, uprint, DEBUG_LEVEL_VERBOSE
from sxmlif import SihotXmlBuilder, ResToSihot, ResResponse, ResFetch, ResSearch
from acif import add_ac_options
from shif import add_sh_options

__version__ = '0.3'

RES_REQ_FILE = 'test/WebResTester.req'
RES_SS_RESP = 'test/OC_SS_Response.xml'
RES_RES_SEARCH_RESP = 'test/OC_RES-SEARCH_Response.xml'

cae = ConsoleApp(__version__, "Test Sihot WEB interface (send, receive, compare)", debug_level_def=DEBUG_LEVEL_VERBOSE,
                 additional_cfg_files=['SihotMktSegExceptions.cfg'])
add_ac_options(cae)
add_sh_options(cae, add_kernel_port=True)

# select reservation by gdsNo (priority) or client ref/matchcode and if both is empty then send file WebResTester.req
cae.add_option('gdsHotel', 'Test reservation identified with gds[@hotel]', '')  # 1098704@3')
cae.add_option('client', 'Test reservations of a client identified with matchcode', '')  # Z008475')  # N617081')
# E362344')  # C605765')


uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), cae.get_option('acuDSN'))
uprint('Server IP/Web-/Kernel-port:', cae.get_option('shServerIP'), cae.get_option('shServerPort'),
       cae.get_option('shServerKernelPort'))
uprint('TCP Timeout/XML Encoding:', cae.get_option('shTimeout'), cae.get_option('shXmlEncoding'))


client_code = cae.get_option('client')
g_ho = cae.get_option('gdsHotel')
gds_no = ho_id = ''
if '@' in g_ho:
    gds_no, ho_id = g_ho.split('@')
else:
    gds_no = g_ho


err_msg = ''
xml = ''
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
        ho_id = crow['RUL_SIHOT_HOTEL']
        xml = acumen_req.xml

    progress.finished(error_msg=err_msg)

elif os.path.isfile(RES_REQ_FILE):
    uprint('####  Preparing XML .....  ####')

    with open(RES_REQ_FILE, 'r') as f:
        xml = f.read()

    sxb = SihotXmlBuilder(cae, use_kernel_interface=False, elem_col_map=(), connect_to_acu=False)
    sxb.xml = xml

    uprint('####  Sending ...........  ####')

    err_msg = sxb.send_to_server()

    uprint('####  Response ..........  ####')
    if err_msg:
        uprint("***   Send Error:", err_msg)
    else:
        uprint("##    SihotXmlBuilder attributes")
        uprint(vars(sxb))

    if getattr(sxb, 'response', None):
        uprint(sxb.response)
        uprint("##    SihotXmlParser attributes")
        uprint(vars(sxb.response))

if xml:
    uprint('####  Parse Sent XML ........  ####')
    sxp = ResResponse(cae)      # SihotXmlParser doesn't have gdsno attribute/base-tag
    sxp.parse_xml(xml)
    uprint("##    ResResponse attributes")
    uprint(vars(sxp))
    ho_id = sxp.id
    gds_no = sxp.gdsno

# gds_no, ho_id = '1098704@3'.split('@')
# cae.set_option('shServerIP', 'tf-sh-sihot1v.acumen.es')
if ho_id and gds_no:
    # now check reservation with ResFetch/SS and ResSearch/RES-SEARCH
    uprint("####  FetchRes ..............  ####")
    rfs = ResFetch(cae)
    ret = rfs.fetch_by_gds_no(ho_id=ho_id, gds_no=gds_no)
    if not isinstance(ret, dict):
        uprint("***   ResFetch error", ret)
    else:
        uprint("##    ResFetch attributes")
        uprint(vars(rfs))
        uprint("##    Request XML:")
        uprint(rfs.xml)
        uprint("##    Parsed Dict:")
        uprint(ret)
        uprint("##    Response XML:")
        uprint(rfs.response.get_xml())
        with open(RES_SS_RESP, 'w') as f:
            f.write(rfs.response.get_xml())

    uprint("####  ResSearch .............  ####")
    rfs = ResSearch(cae)
    ret = rfs.search(hotel_id=ho_id, gdsno=gds_no)
    if not isinstance(ret, list):
        uprint("***     ResSearch error", ret)
    else:
        uprint("##    ResSearch attributes")
        uprint(vars(rfs))
        uprint("##    XML:")
        uprint(rfs.xml)
        uprint("##    Parsed List:")
        uprint(ret)
        uprint("##    Response XML:")
        uprint(rfs.response.get_xml())
        with open(RES_RES_SEARCH_RESP, 'w') as f:
            f.write(rfs.response.get_xml())

cae.shutdown()
