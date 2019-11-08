"""
In Salesforce we either creating an Button that calls an Apex Class that makes an API call to this server
or we will use a Workflow, triggered by a record update to send an Outbound Message to this server.

Outbound Example with twisted: https://salesforce.stackexchange.com/questions/94279/parsing-outbound-message-in-python
and https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_quickstart_intro.htm

Version History:
    0.1     first beta
    0.2     refactored to use ae.sys_data.
    0.3     prepared first production version.
    0.4     enhanced error handling and reporting to caller.
    0.5     added separate system environments and new URLs for the TEST/LIVE systems.
    0.6     beautified and hardened error notification and logging.
    0.7     added ResGdsNo to json return of res_change() route method.
    0.8     enhanced error logging and skipping/handling of ignorable sihot errors.

DISTRIBUTE:

Salesforce check/prepare:
- Add host URL in Salesforce/Setup/Remote Site config options for to authorize endpoint addresses:
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
from functools import wraps

__version__ = '0.8'

from traceback import format_exc
import os
import sys

# change working dir so bottle.py will be find by next import statement (also for relative paths and template lookup)
os.chdir(os.path.dirname(__file__))
sys.path.append(os.path.dirname(__file__))
from bottle import default_app, request, response, static_file, template, run, makelist

from ae.sys_core_sh import SDI_SH
from ae.core import DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE, po
from ae.sys_data import FAD_FROM, Record, ACTION_UPSERT, ACTION_INSERT, ACTION_DELETE, field_name_idx_path
from ae.console import ConsoleApp
from sys_core_sf import field_from_converters, SDI_SF
from ae.sys_data_sh import ResSender
from sys_data_ass import add_ass_options, init_ass_data


# app and application will be used when used as server plug-in in apache/nginx
app = application = default_app()


# initialize multiple, separate system environments for TEST and LIVE
def init_env(sys_env_id):
    cae = ConsoleApp("Web Service {} Server".format(sys_env_id),
                     additional_cfg_files=['SihotMktSegExceptions.cfg'],
                     multi_threading=True, suppress_stdout=True, sys_env_id=sys_env_id)
    ass_options = add_ass_options(cae, add_kernel_port=True)
    ass_data = init_ass_data(cae, ass_options)
    return cae, ass_data['assSysData'], ass_data['notification']


cae_test, asd_test, notification_test = init_env('TEST')
cae_live, asd_live, notification_live = init_env('LIVE')


def route_also_test_sys_env(route_path, method='GET', **route_kwargs):
    """
    decorator adding system environment variables as args (cae, asd and notification) to route methods.
    """
    test_path_prefix = '/test'
    ext_path = list()
    for p in makelist(route_path):
        assert p.startswith("/")
        ext_path.append(p)
        ext_path.append(test_path_prefix + p)
    assert method

    def decorator(func):
        @app.route(path=ext_path, method=method, **route_kwargs)
        @wraps(func)
        def wrapper(*args, **kwargs):
            path = request.path
            assert path.startswith("/")
            cae, asd, notification = \
                (cae_test, asd_test, notification_test) if path.startswith(test_path_prefix) else \
                (cae_live, asd_live, notification_live)
            cae.dpo("  ##  Client requested {} with args={} and kwargs={}".format(path, args, kwargs))
            ret = func(cae, asd, notification, *args, **kwargs)
            cae.dpo("  ##  Sihot Server response=\n{}".format(ret))
            return ret
        return wrapper
    return decorator


# ------  BOTTLE WEB SERVICE ROUTES  -------------------------------------------

@route_also_test_sys_env('/hello/<name>')
def get_hello(_cae, _asd, _notification, name='world'):
    return "hello " + name


@route_also_test_sys_env('/static/<filename>')
def get_static_static_file(_cae, _asd, _notification, filename):
    return static_file(filename, root='./static')


@route_also_test_sys_env('/page/<page_name>')
def get_page(_cae, _asd, _notification, page_name):       # return a page that has been rendered using a template
    return template('page', page_name=page_name)


@route_also_test_sys_env('/avail_rooms')
def get_avail_rooms(_, asd, _notification):
    rq = request.query
    rooms = asd.sh_avail_rooms(hotel_ids=rq['hotel_ids'], room_cat_prefix=rq['room_cat_prefix'], day=rq['day'])
    return str(rooms)


@route_also_test_sys_env('/res/count')
def get_res_count(_cae, asd, _notification):
    rqi = " ".join([k + "=" + str(v) for k, v in request.query.items()])
    return "Number of reservations" + (" with " + rqi if len(rqi) else "") \
           + " is " + str(asd.sh_count_res(**request.query))


@route_also_test_sys_env('/res/get')
def get_res_data(_cae, asd, _notification):
    rec = asd.sh_res_data(**request.query)
    ret = dict(ErrorMessage="")
    if isinstance(rec, Record):
        # using FromSh rec values for to send datetime as ISO strings
        ret.update(rec.to_dict(use_system_key=False, system=SDI_SH, direction=FAD_FROM))
        if not ret.get('ResRoomNo', False) and rec.val('ResPersons', 0, 'RoomNo'):
            ret['ResRoomNo'] = rec.val('ResPersons', 0, 'RoomNo')
        # ret['ResRoomNo'] = rec.val('ResRoomNo') or rec.val('ResPersons', 0, 'RoomNo')
    else:
        ret['ErrorMessage'] = rec
    return ret


@route_also_test_sys_env('/res/<action>', method='POST')
def change_res(cae, _asd, notification, action):
    body = sh_res_action(cae, notification, action)
    return body


# -----  HELPER FUNCTIONS  -------------------------------------------

def add_log_entry(warning_msg="", error_msg="", importance=2, cae=None, notification=None):
    seps = '\n' * (importance - 2)
    msg = seps + ' ' * (4 - importance) + ('*' if error_msg else '#') * importance + '  ' + error_msg
    if warning_msg:
        if error_msg:
            msg += '\n' + '.' * 6
        msg += warning_msg
    _print_method = cae.dpo if cae else po
    _print_method(msg)
    if error_msg and notification:
        notification_err = notification.send_notification(msg, subject="SihotServer error notification",
                                                          body_style='plain')
        if notification_err:
            _print_method(error_msg + "\n      Notification send error: " + notification_err)


# ------  ROUTE/SERVICE HANDLERS  ----------------------------------


def sh_res_action(cae, notification, action, res_id=None, method='POST'):
    supported_actions = (ACTION_UPSERT, ACTION_INSERT, ACTION_DELETE)
    err = msg = ""
    ret = dict(ErrorMessage=err, WarningMessage=msg)
    res_json = dict()
    debug_level = cae.get_opt('debugLevel')

    res_send = ResSender(cae)
    rec = Record(system=SDI_SF, direction=FAD_FROM).add_system_fields(res_send.elem_map)

    if action.upper() not in supported_actions:
        err = "Reservation {} for ID {} with action {} not implemented; use one of supported actions ({})" \
            .format(method, res_id, action, supported_actions)
        add_log_entry(error_msg=err, importance=4, cae=cae, notification=notification)
    elif debug_level >= DEBUG_LEVEL_VERBOSE:
        headers_string = ['{}: {}'.format(h, request.headers.get(h)) for h in request.headers.keys()]
        msg = "sh_res_action({}, {}, {}/{}) received request: URL={}; header={!r}; body={!r}; query={!r}" \
            .format(action, res_id, method, request.method, request.url, headers_string,
                    request.body.getvalue(), request.query_string)
        add_log_entry(warning_msg=msg, cae=cae, notification=notification)

    rec.set_val(action.upper(), 'ResAction', system=SDI_SF, direction=FAD_FROM)  # overwrite with URL action

    if not err:
        try:
            res_json = request.json         # web service arguments as dict
            if res_json is None:
                err = "JSON arguments missing"
                msg += "\n      got request {!r} but body with JSON is empty".format(request)
                add_log_entry(error_msg=err, warning_msg=msg, importance=3, cae=cae, notification=notification)
        except Exception as e:
            err = "retrieve JSON arguments exception='{}'\n{}".format(e, format_exc())

    if not err:
        try:
            for name, value in res_json.items():
                idx_path = field_name_idx_path(name, return_root_fields=True)
                rec.set_val(value, *idx_path, system=SDI_SF, direction=FAD_FROM,
                            converter=field_from_converters.get(idx_path[-1]) or field_from_converters.get(idx_path[0]),
                            to_value_type=True)
            rec.pull(SDI_SF)
        except Exception as e:
            err = "parse JSON exception='{}'\n{}".format(e, format_exc())

    if not err:
        try:
            err, msg = res_send.send_rec(rec)

            if not err and res_send.response.objid:     # objid is empty if sihot error is skipped/ignorable
                res_no_tuple = res_send.get_res_no()
                if res_no_tuple[0] is None:
                    err = res_no_tuple[1]
                else:
                    response.status = 200
                    ho_id, res_id, sub_id, gds_no = res_no_tuple
                    ret.update(ResHotelId=ho_id, ResId=res_id, ResSubId=sub_id, ResGdsNo=gds_no)
        except Exception as e:
            err = "send to Sihot exception='{}'\n{}".format(e, format_exc())

    if err:
        ret['ErrorMessage'] += err
    if msg:
        ret['WarningMessage'] += msg

    if ret['ErrorMessage'] or debug_level >= DEBUG_LEVEL_ENABLED:
        add_log_entry(warning_msg="sh_res_action({}, {}, {}) called with JSON: {}; responding to SF: {}"
                      .format(action, res_id, method, res_json, ret),
                      error_msg=ret['ErrorMessage'],
                      importance=4,
                      cae=cae, notification=notification)

    return ret


# ------  DEBUG HELPERS  -------------------------------------------

class StripPathMiddleware(object):      # remove slash from request
    def __init__(self, a):
        self.a = a

    def __call__(self, e, h):
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
        return self.a(e, h)


if __name__ == '__main__':      # use bottle server only in debug mode on dev machine
    err_code = 0
    try:
        run(app=StripPathMiddleware(app), server='python_server', host='0.0.0.0', port=9090)
    except Exception as ex:
        add_log_entry(error_msg="run() exception='{}'\n{}".format(ex, format_exc()),
                      cae=cae_live or cae_test, notification=notification_live or notification_test)
        err_code = 9639
    cae_live.shutdown(exit_code=err_code)   # shutdown second ConsoleApp instance first (close the logs, no sys.exit())
