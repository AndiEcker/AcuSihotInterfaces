"""
In Salesforce we either creating an Button that calls an Apex Class that makes an API call to this server
or we will use a Workflow, triggered by a record update to send an Outbound Message to this server.

Outbound Example with twisted: https://salesforce.stackexchange.com/questions/94279/parsing-outbound-message-in-python
and https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_quickstart_intro.htm


DISTRIBUTE:

Prerequisites - check values:
- <ws_url>  URL of web service (endpoint/class/action), e.g. 'https://web1v-tf.signallia.com/res/upsert'

Salesforce check/prepare:
- Authorize Endpoint Addresses:
    see https://trailhead.salesforce.com/modules/
    ./apex_integration_services/units/apex_integration_callouts#apex_integration_callouts_authorizing
- APEX code template/example: see SihotServerApex.js

Web-Service server check/prepare:
- Setup apache: https://stackoverflow.com/questions/17678037/running-apache-bottle-python?rq=1
  and https://stackoverflow.com/questions/36901905/deploying-a-bottle-py-app-with-apache-mod-wsgi-on-ubuntu-16-04
- Alternative setup nginx+uwsgi: https://michael.lustfield.net/nginx/bottle-uwsgi-nginx-quickstart

"""

from bottle import Bottle, request, response, static_file, template, run

from ae_console_app import ConsoleApp, uprint, DEBUG_LEVEL_VERBOSE
from ae_notification import add_notification_options, init_notification
from shif import add_sh_options, ResSender

__version__ = '0.1'

cae = ConsoleApp(__version__, "Pass requests from Salesforce-CRM onto Sihot-PMS",
                 additional_cfg_files=['SihotMktSegExceptions.cfg'], multi_threading=True)
add_sh_options(cae)
add_notification_options(cae)

debug_level = cae.get_option('debugLevel')
notification, _ = init_notification(cae, cae.get_option('shServerIP'))


def add_log_entry(error_msg="", warning_msg="", importance=2):
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


# app and application will be used when used as server plug-in in apache/nginx
app = application = Bottle()


@app.route('/res/<action>')
def res_action(action):       # process reservation action, e.g. upsert
    # web service parameters are available as dict in request.json
    cae.dprint('res' + ':' + action + ':' + request.json, minimum_debug_level=DEBUG_LEVEL_VERBOSE)
    assert action == 'upsert'

    res_send = ResSender(cae)
    err, msg = res_send.send_row(request.json)
    if err or msg:
        add_log_entry(error_msg=err, warning_msg=msg, importance=3 if err else 2)
    if err:
        res_dict = dict(Error=err, Message=msg)
    else:
        response.status_code = 400
        ho_id, res_id, sub_id = res_send.get_res_no()
        res_dict = dict(Sihot_Hotel_Id=ho_id, Sihot_Res_Id=res_id, Sihot_Sub_Id=sub_id)
    return res_dict


@app.route('/static/<filename>')
def static(filename):
    return static_file(filename, root='./static')


@app.route('/')
def show_index():
    return 'Hello'


@app.route('/page/<page_name>')
def show_page(page_name):       # return a page that has been rendered using a template
    return template('page', page_name=page_name)


class StripPathMiddleware(object):      # remove slash from request
    def __init__(self, a):
        self.a = a

    def __call__(self, e, h):
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
        return self.a(e, h)


if __name__ == '__main__':      # use bottle server only in debug mode on dev machine
    run(app=StripPathMiddleware(app), server='python_server', host='0.0.0.0', port=9090)
