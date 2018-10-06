"""
In Salesforce we either creating an Button that calls an Apex Class that makes an API call to this server
or we will use a Workflow, triggered by a record update to send an Outbound Message to this server.

Outbound Example with twisted: https://salesforce.stackexchange.com/questions/94279/parsing-outbound-message-in-python
and https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_quickstart_intro.htm


DISTRIBUTE:

Prerequisites - check values:
- URL of web service (endpoint/class/action), e.g. 'https://services.signallia.com/res/upsert'

Salesforce check/prepare:
- Add host URL in Salesforce/Setup/Remote Site Settings for to authorize endpoint addresses:
    see https://trailhead.salesforce.com/modules/
    ./apex_integration_services/units/apex_integration_callouts#apex_integration_callouts_authorizing
- Implement APEX code template/example: see e.g. SihotServerApex.apex

Http-/Web-server check/prepare:
- Setup apache (done by Davide): https://stackoverflow.com/questions/17678037/running-apache-bottle-python?rq=1
  and https://stackoverflow.com/questions/36901905/deploying-a-bottle-py-app-with-apache-mod-wsgi-on-ubuntu-16-04
- Alternative setup nginx+uwsgi: https://michael.lustfield.net/nginx/bottle-uwsgi-nginx-quickstart

Web-Service server check/prepare:
- copy files to distribution sync folder (using build_ws_*.cmd).
- synchronize sync folder content to http/web server (using e.g. WinSCP or other SFTP client).

"""

__version__ = '0.1'

# change working dir so bottle.py will be find by next import statement (also for relative paths and template lookup)
import os
import sys
os.chdir(os.path.dirname(__file__))
sys.path.append(os.path.dirname(__file__))

from bottle import default_app, request, response, static_file, template, run

from ae_console_app import ConsoleApp, uprint, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE
from shif import ResSender
from ass_sys_data import add_ass_options, init_ass_data

cae = ConsoleApp(__version__, "Web Service Server", additional_cfg_files=['SihotMktSegExceptions.cfg'],
                 multi_threading=True, suppress_stdout=True)
ass_options = add_ass_options(cae)

debug_level = cae.get_option('debugLevel')
ass_data = init_ass_data(cae, ass_options)
conf_data = ass_data['assSysData']
notification = ass_data['notification']

# app and application will be used when used as server plug-in in apache/nginx
app = application = default_app()


# ------  BOTTLE ROUTES  -------------------------------------------

@app.route('/hello/<name>')
def get_hello(name='world'):
    return "hello " + name


@app.route('/static/<filename>')
def get_static_static_file(filename):
    return static_file(filename, root='./static')


@app.route('/page/<page_name>')
def get_page(page_name):       # return a page that has been rendered using a template
    return template('page', page_name=page_name)


@app.route('/avail_rooms')
def get_avail_rooms():
    rd = request.json
    rooms = conf_data.sh_avail_rooms(hotel_ids=rd['hotel_ids'], room_cat_prefix=rd['room_cat_prefix'], day=rd['day'])
    return str(rooms)


@app.route('/res/count')
def get_res_count():
    rqi = " ".join([k + "=" + str(v) for k, v in request.query.items()])
    return "Number of reservations" + (" with " + rqi if len(rqi) else "") \
           + " is " + str(conf_data.sh_count_res(**request.query))


@app.route('/res/get')
def get_res_data():
    return conf_data.sh_res_data(**request.query)


@app.route('/res/<action>', method='PUSH')
def push_res(action):
    if action == 'upsert':
        body = res_upsert()
    else:
        body = "Reservation PUSH with action {} not implemented".format(action)
        add_log_entry(body, minimum_debug_level=DEBUG_LEVEL_ENABLED)
    return body


@app.route('/res/<action>/<res_id>', method='PUT')
def put_res(action, res_id):
    if action == 'upsert':
        body = res_upsert(res_id)
    else:
        body = "Reservation PUT for ID {} with action {} not implemented".format(res_id, action)
        add_log_entry(body, minimum_debug_level=DEBUG_LEVEL_ENABLED)
    return body


# -----  HELPER METHODS  -------------------------------------------

def add_log_entry(warning_msg="", error_msg="", importance=2, minimum_debug_level=DEBUG_LEVEL_VERBOSE):
    if not error_msg and debug_level < minimum_debug_level:
        return      # suppress notification - nothing to do/show
    seps = '\n' * (importance - 2)
    msg = seps + ' ' * (4 - importance) + ('*' if error_msg else '#') * importance + '  ' + error_msg
    if warning_msg:
        if error_msg:
            msg += '\n' + '.' * 6
        msg += warning_msg
    uprint(msg)
    if error_msg and notification:
        notification_err = notification.send_notification(msg, subject="SihotServer error notification")
        if notification_err:
            uprint(error_msg + "\n      Notification send error: " + notification_err)


# ------  ROUTE/SERVICE HANDLERS  ----------------------------------


def res_upsert(res_id=''):
    # web service parameters are available as dict in request.json
    res_json = request.json
    add_log_entry("res_upsert({}): {}".format(res_id, res_json))

    # added Q&D for to support new parameter/field names
    tt = dict(HotelIdc='RUL_SIHOT_HOTEL', Numberc='', SubNumberc='', GdsNoc='SIHOT_GDSNO',
              Arrivalc='ARR_DATE', Departurec='DEP_DATE',
              RoomCatc='RUL_SIHOT_CAT', AcumenClientRefpc='OC_CODE', Statusc='SH_RES_TYPE', Actionc='RUL_ACTION',
              BaordIdc='RUL_SIHOT_PACK', SourceIdc='RU_SOURCE', Notec='SIHOT_NOTE', Adultsc='RU_ADULTS',
              Childrenc='RU_CHILDREN')
    res_data = {tt[k]: v for k, v in res_json.items() if k in tt}

    if res_id and not res_data.get('RUL_ACTION'):      # res_id is passed also within request
        res_data['RUL_ACTION'] = 'UPDATE'

    res_send = ResSender(cae)
    err, msg = res_send.send_row(res_data)
    if err or msg:
        add_log_entry(warning_msg=msg, error_msg=err, importance=3 if err else 2)
    if err:
        res_dict = dict(Error=err, Message=msg)
    else:
        response.status_code = 400
        ho_id, res_id, sub_id = res_send.get_res_no()
        # res_dict = dict(Sihot_Hotel_Id=ho_id, Sihot_Res_Id=res_id, Sihot_Sub_Id=sub_id)
        res_dict = dict(HotelIdc=ho_id, Numberc=res_id, SubNumberc=sub_id)
    return res_dict


# ------  DEBUG HELPERS  -------------------------------------------

class StripPathMiddleware(object):      # remove slash from request
    def __init__(self, a):
        self.a = a

    def __call__(self, e, h):
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
        return self.a(e, h)


if __name__ == '__main__':      # use bottle server only in debug mode on dev machine
    run(app=StripPathMiddleware(app), server='python_server', host='0.0.0.0', port=9090)
