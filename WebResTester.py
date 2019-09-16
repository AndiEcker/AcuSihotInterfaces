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

cae = ConsoleApp("Test Sihot WEB interface (send, receive, compare)", debug_level=DEBUG_LEVEL_VERBOSE,
                 additional_cfg_files=['SihotMktSegExceptions.cfg'])
add_ac_options(cae)
add_sh_options(cae, add_kernel_port=True)

# select reservation by gdsNo (priority) or client ref/matchcode and if both is empty then send file WebResTester.req
cae.add_opt('gdsHotel', "Test reservation identified with gds[@hotel]", '')  # 1098704@3')
cae.add_opt('client', "Test reservations of a client identified with matchcode", '')  # Z008475')  # N617081')
# E362344')  # C605765')


cae.po("Acumen Usr/DSN:", cae.get_opt('acuUser'), cae.get_opt('acuDSN'))
cae.po("Server IP/Web-/Kernel-port:", cae.get_opt('shServerIP'), cae.get_opt(SDF_SH_WEB_PORT),
       cae.get_opt(SDF_SH_KERNEL_PORT))
cae.po("TCP Timeout/XML Encoding:", cae.get_opt(SDF_SH_TIMEOUT), cae.get_opt(SDF_SH_XML_ENCODING))


client_code = cae.get_opt('client')
g_ho = cae.get_opt('gdsHotel')
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

    cae.po('####  Fetching client res  ####')

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
    cae.po('####  Preparing XML .....  ####')

    with open(RES_REQ_FILE) as f:
        xml = f.read()

    sxb = SihotXmlBuilder(cae)
    sxb.xml = xml

    cae.po('####  Sending ...........  ####')

    err_msg = sxb.send_to_server()

    cae.po('####  Response ..........  ####')
    if err_msg:
        cae.po("***   Send Error:", err_msg)
    else:
        cae.po("##    SihotXmlBuilder attributes")
        cae.po(vars(sxb))

    if getattr(sxb, 'response', None):
        cae.po(sxb.response)
        cae.po("##    SihotXmlParser attributes")
        cae.po(vars(sxb.response))

if xml:
    cae.po('####  Parse Sent XML ........  ####')
    sxp = ResResponse(cae)      # SihotXmlParser doesn't have gdsno attribute/base-tag
    sxp.parse_xml(xml)
    cae.po("##    ResResponse attributes")
    cae.po(vars(sxp))
    ho_id = sxp.id
    gds_no = sxp.gdsno

# gds_no, ho_id = '1098704@3'.split('@')
# cae.set_opt('shServerIP', 'tf-sh-sihot1v.acumen.es')
if ho_id and gds_no:
    # now check reservation with ResFetch/SS and ResSearch/RES-SEARCH
    cae.po("####  FetchRes ..............  ####")
    rfs = ResFetch(cae)
    ret = rfs.fetch_by_gds_no(ho_id=ho_id, gds_no=gds_no)
    if not isinstance(ret, dict):
        cae.po("***   ResFetch error", ret)
    else:
        cae.po("##    ResFetch attributes")
        cae.po(vars(rfs))
        cae.po("##    Request XML:")
        cae.po(rfs.xml)
        cae.po("##    Parsed Dict:")
        cae.po(ret)
        cae.po("##    Response XML:")
        cae.po(rfs.response.get_xml())
        with open(RES_SS_RESP, 'w') as f:
            f.write(rfs.response.get_xml())

    cae.po("####  ResSearch .............  ####")
    rfs = ResSearch(cae)
    ret = rfs.search_res(hotel_id=ho_id, gds_no=gds_no)
    if not isinstance(ret, list):
        cae.po("***     ResSearch error", ret)
    else:
        cae.po("##    ResSearch attributes")
        cae.po(vars(rfs))
        cae.po("##    XML:")
        cae.po(rfs.xml)
        cae.po("##    Parsed List:")
        cae.po(ret)
        cae.po("##    Response XML:")
        cae.po(rfs.response.get_xml())
        with open(RES_RES_SEARCH_RESP, 'w') as f:
            f.write(rfs.response.get_xml())

cae.shutdown()
