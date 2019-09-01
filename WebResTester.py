import os

from sys_data_ids import SDF_SH_WEB_PORT, SDF_SH_KERNEL_PORT, SDF_SH_TIMEOUT, SDF_SH_XML_ENCODING
from ae.core import DEBUG_LEVEL_VERBOSE
from ae.console_app import ConsoleApp
from ae.progress import Progress
from sxmlif import SihotXmlBuilder, ResResponse
from acif import add_ac_options, AcuResToSihot
from shif import add_sh_options, ResFetch, ResSearch

__version__ = '0.3'

RES_REQ_FILE = 'test/WebResTester.req'
RES_SS_RESP = 'test/OC_SS_Response.xml'
RES_RES_SEARCH_RESP = 'test/OC_RES-SEARCH_Response.xml'

cae = ConsoleApp(__version__, "Test Sihot WEB interface (send, receive, compare)", debug_level_def=DEBUG_LEVEL_VERBOSE,
                 additional_cfg_files=['SihotMktSegExceptions.cfg'])
add_ac_options(cae)
add_sh_options(cae, add_kernel_port=True)

# select reservation by gdsNo (priority) or client ref/matchcode and if both is empty then send file WebResTester.req
cae.add_option('gdsHotel', "Test reservation identified with gds[@hotel]", '')  # 1098704@3')
cae.add_option('client', "Test reservations of a client identified with matchcode", '')  # Z008475')  # N617081')
# E362344')  # C605765')


cae.uprint("Acumen Usr/DSN:", cae.get_option('acuUser'), cae.get_option('acuDSN'))
cae.uprint("Server IP/Web-/Kernel-port:", cae.get_option('shServerIP'), cae.get_option(SDF_SH_WEB_PORT),
           cae.get_option(SDF_SH_KERNEL_PORT))
cae.uprint("TCP Timeout/XML Encoding:", cae.get_option(SDF_SH_TIMEOUT), cae.get_option(SDF_SH_XML_ENCODING))


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

    cae.uprint('####  Fetching client res  ####')

    acumen_res = AcuResToSihot(cae)
    err_msg = acumen_res.fetch_from_acu_by_aru("RU_CODE = " + gds_no if gds_no else "CD_CODE = '" + client_code + "'")
    if not err_msg and not len(acumen_res.recs):
        if gds_no:
            err_msg = acumen_res.fetch_all_valid_from_acu(where_group_order="RU_CODE = " + gds_no)
        else:
            err_msg = acumen_res.fetch_from_acu_by_cd(client_code)      # UNFILTERED !!! (possibly inactive hotel)
    progress = Progress(cae, start_counter=len(acumen_res.recs),
                        start_msg='####  Prepare sending of {total_count} reservation requests' + client_msg,
                        nothing_to_do_msg='****  SihotMigration: acumen_res fetch returning no recs')

    for rec in acumen_res.recs:
        err_msg = acumen_res.send_res_to_sihot(rec)
        acumen_res.ora_db.commit()
        progress.next(processed_id=str(rec['ResGdsNo']), error_msg=err_msg)
        ho_id = rec['ResHotelId']
        xml = acumen_res.xml

    progress.finished(error_msg=err_msg)

elif os.path.isfile(RES_REQ_FILE):
    cae.uprint('####  Preparing XML .....  ####')

    with open(RES_REQ_FILE) as f:
        xml = f.read()

    sxb = SihotXmlBuilder(cae)
    sxb.xml = xml

    cae.uprint('####  Sending ...........  ####')

    err_msg = sxb.send_to_server()

    cae.uprint('####  Response ..........  ####')
    if err_msg:
        cae.uprint("***   Send Error:", err_msg)
    else:
        cae.uprint("##    SihotXmlBuilder attributes")
        cae.uprint(vars(sxb))

    if getattr(sxb, 'response', None):
        cae.uprint(sxb.response)
        cae.uprint("##    SihotXmlParser attributes")
        cae.uprint(vars(sxb.response))

if xml:
    cae.uprint('####  Parse Sent XML ........  ####')
    sxp = ResResponse(cae)      # SihotXmlParser doesn't have gdsno attribute/base-tag
    sxp.parse_xml(xml)
    cae.uprint("##    ResResponse attributes")
    cae.uprint(vars(sxp))
    ho_id = sxp.id
    gds_no = sxp.gdsno

# gds_no, ho_id = '1098704@3'.split('@')
# cae.set_option('shServerIP', 'tf-sh-sihot1v.acumen.es')
if ho_id and gds_no:
    # now check reservation with ResFetch/SS and ResSearch/RES-SEARCH
    cae.uprint("####  FetchRes ..............  ####")
    rfs = ResFetch(cae)
    ret = rfs.fetch_by_gds_no(ho_id=ho_id, gds_no=gds_no)
    if not isinstance(ret, dict):
        cae.uprint("***   ResFetch error", ret)
    else:
        cae.uprint("##    ResFetch attributes")
        cae.uprint(vars(rfs))
        cae.uprint("##    Request XML:")
        cae.uprint(rfs.xml)
        cae.uprint("##    Parsed Dict:")
        cae.uprint(ret)
        cae.uprint("##    Response XML:")
        cae.uprint(rfs.response.get_xml())
        with open(RES_SS_RESP, 'w') as f:
            f.write(rfs.response.get_xml())

    cae.uprint("####  ResSearch .............  ####")
    rfs = ResSearch(cae)
    ret = rfs.search_res(hotel_id=ho_id, gds_no=gds_no)
    if not isinstance(ret, list):
        cae.uprint("***     ResSearch error", ret)
    else:
        cae.uprint("##    ResSearch attributes")
        cae.uprint(vars(rfs))
        cae.uprint("##    XML:")
        cae.uprint(rfs.xml)
        cae.uprint("##    Parsed List:")
        cae.uprint(ret)
        cae.uprint("##    Response XML:")
        cae.uprint(rfs.response.get_xml())
        with open(RES_RES_SEARCH_RESP, 'w') as f:
            f.write(rfs.response.get_xml())

cae.shutdown()
