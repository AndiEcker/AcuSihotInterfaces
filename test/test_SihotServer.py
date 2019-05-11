"""
    SihotServer integration tests against TEST systems - some read-only tests are also done against LIVE/production.
"""
import pytest

import datetime
import requests
from configparser import ConfigParser


test_path_prefix = '/test'

cfg = ConfigParser()
cfg.optionxform = str  # for case-sensitive config vars
cfg.read(['../.console_app_env.cfg', '../.sys_envTEST.cfg'])
# simple cfg.get() call does not convert config value into list/dict without using ae_console_app.Setting()
ws_host = cfg.get('Settings', 'wsHost')
assert ws_host


def add_parametrize_defaults(arg_dicts):
    global ws_host
    args_list = list()
    for args in arg_dicts:
        path = args['path']
        args_list.append((ws_host + test_path_prefix + path, args['text_fragment'],
                          args.get('params'), args.get('status', 200), args.get('json_values')))
        if 'skip_live' not in args:
            args_list.append((ws_host + path, args['text_fragment'],
                              args.get('params'), args.get('status', 200), args.get('json_values')))
    return args_list


@pytest.mark.parametrize('path,text_fragment,params,status,json_values',
                         add_parametrize_defaults([dict(path='/xxx/test_word', text_fragment="Not found", status=404),
                                                   dict(path='/hello/test_word', text_fragment="hello test_word"),
                                                   dict(path='/static/test.file', text_fragment="test file content"),
                                                   dict(path='/page/test', text_fragment="not found", status=500),
                                                   dict(path='/avail_rooms', text_fragment="4",
                                                        params=dict(hotel_ids=['1'], room_cat_prefix='1',
                                                                    day=datetime.date(2017, 9, 14)),
                                                        skip_live=True),    # on LIVE the result is 5 not 4 ?!?!?
                                                   dict(path='/res/get', text_fragment="0803",
                                                        params=dict(hotel_id=4, gds_no=899993),
                                                        json_values=dict(ErrorMessage="", ResPersons0RoomNo="0803",
                                                                         ResRoomNo="0803", ResGdsNo="899993")),
                                                   dict(path='/res/get', text_fragment="0803",
                                                        params=dict(hotel_id=4, res_id='33220', sub_id='1'),
                                                        json_values=dict(ErrorMessage="", ResPersons0RoomNo="0803",
                                                                         ResRoomNo="0803", ResGdsNo="899993")),
                                                   dict(path='/res/count', text_fragment="4",
                                                        params=dict(hotel_ids=['999'], room_cat_prefix='1JNR',
                                                                    day=datetime.date(2017, 9, 14))),
                                                   ]))
def test_read_only_services(path, text_fragment, params, status, json_values):
    response = requests.get(path, params=params)
    print(response.url)
    assert text_fragment in response.text
    assert response.status_code == status
    if json_values:
        assert response.text.startswith("{")
        js = response.json()
        for k, v in json_values.items():
            assert js.get(k) == v


class ProxyNotWorkingTestRequestsConnection:
    def test_github_events(self, console_app_env):
        _ = self

        url = 'https://api.github.com/events'
        with_proxy = True
        if with_proxy:
            user = console_app_env.get_config('wsUser')
            password = console_app_env.get_config('wsPassword')
            proxy_string = 'http://10.103.1.10:8080'
            # proxy_string = 'http://{}:{}@proxy.acumen.es:8080'.format(user, password)
            # proxy_string = 'http://{}:{}@10.103.1.10:8080'.format(user, password)
            # proxy_string = 'http://{}@acumen:{}@10.103.1.10:8080'.format(user, password)

            s = requests.Session()
            s.trust_env = False
            s.proxies = dict(http=proxy_string, https=proxy_string)
            from requests.auth import HTTPProxyAuth
            s.auth = HTTPProxyAuth(user, password)
            response = s.get(url, proxies=s.proxies, auth=s.auth)
        else:
            response = requests.get(url)
        print(response.url)
        print(response.json())


class ApacheRestartNotWorkingTestCreateOrChangeRes:
    def test_create_res(self):
        _ = self

        gds_no = 'TEST-RES-NEW-123456'
        params = dict(ResHotelId='1', ResGdsNo=gds_no, ResMktSegment='TO', ResRoomCat='1JNR',
                      ResArrival='2022-02-22', ResDeparture='2022-02-24',
                      Surname='CreateTester')
        response = requests.post(ws_host + test_path_prefix + '/res/insert', json=params)
        print(response.url)
        assert response.status_code == 200
        js = response.json()
        assert js.get('ErrorMessage') == ""
        assert js.get('ResGsdNo') == gds_no
