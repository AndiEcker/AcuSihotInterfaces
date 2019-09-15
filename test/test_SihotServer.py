"""
    SihotServer integration tests against TEST systems - some read-only tests are also done against LIVE/production.
"""
import pytest

import datetime
import requests
from configparser import ConfigParser

from shif import ResFetch

test_path_prefix = '/test'

cfg = ConfigParser()
cfg.optionxform = str  # for case-sensitive config vars
cfg.read(['../.app_env.cfg', '../.sys_envTEST.cfg'])
# simple cfg.get() call does not convert config value into list/dict without using ae.console_app.Setting()
ws_host = cfg.get('aeOptions', 'wsHost')
assert ws_host


def add_parametrize_defaults(arg_dicts):
    global ws_host
    args_list = list()
    for args in arg_dicts:
        used_args = list()
        path = args['path']
        txt = args.get('text_fragment', "")
        if txt:
            used_args.append(txt)
        used_args.append(args.get('params'))
        used_args.append(args.get('status', 200))
        used_args.append(args.get('json_values'))
        rec = args.get('rec')
        if rec:
            used_args.append(rec)

        args_list.append((ws_host + test_path_prefix + path,) + tuple(used_args))
        if not args.get('skip_live', False):
            args_list.append((ws_host + path,) + tuple(used_args))

    return args_list


@pytest.mark.parametrize(
    'path,text_fragment,params,status,json_values',
    add_parametrize_defaults([
        dict(path='/xxx/test_word', text_fragment="Not found", status=404),
        dict(path='/hello/test_word', text_fragment="hello test_word"),
        dict(path='/static/test.file', text_fragment="test file content"),
        dict(path='/page/test', text_fragment="not found", status=500),
        dict(
            path='/avail_rooms', text_fragment="4",
            params=dict(hotel_ids=['1'], room_cat_prefix='1', day=datetime.date(2017, 9, 14)),
            skip_live=True),  # on LIVE the result is 5 not 4 ?!?!?
        dict(
            path='/res/get', text_fragment="0803",
            params=dict(hotel_id=4, gds_no=899993),
            json_values=dict(ErrorMessage="", ResPersons0RoomNo="0803", ResRoomNo="0803", ResGdsNo="899993")),
        dict(
            path='/res/get', text_fragment="0803",
            params=dict(hotel_id=4, res_id='33220', sub_id='1'),
            json_values=dict(ErrorMessage="", ResPersons0RoomNo="0803", ResRoomNo="0803", ResGdsNo="899993")),
        dict(
            path='/res/count', text_fragment="4",
            params=dict(hotel_ids=['999'], room_cat_prefix='1JNR', day=datetime.date(2017, 9, 14))),
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


@pytest.mark.parametrize(
    'path,params,status,json_values,rec',
    add_parametrize_defaults([
        dict(
            path='/res/insert',
            params=dict(
                ResHotelId='1', ResGdsNo='TEST-RES-NEW-123456', ResMktSegment='TO', ResRoomCat='1JNR',
                ResArrival='2022-02-22', ResDeparture='2022-02-24', Surname='CreateTester'),
            json_values=dict(ErrorMessage="", ResHotelId='1', ResGdsNo='TEST-RES-NEW-123456', ResSubId='1'),
            rec=dict(
                ResHotelId='1', ResGdsNo='TEST-RES-NEW-123456', ResMktSegment='TO', ResRoomCat='1JNR',
                ResArrival=datetime.date(2022, 2, 22), ResDeparture=datetime.date(2022, 2, 24), Surname='CreateTester'),
            skip_live=True),
        dict(
            path='/res/upsert',
            params=dict(
                ResHotelId='4', ResGdsNo='TEST-RES-NEW-123456', ResMktSegment='OT', ResRoomCat='STDP',
                ResArrival='2022-02-21', ResDeparture='2022-02-25', Surname='CreateTester'),
            json_values=dict(ErrorMessage="", ResHotelId='4', ResGdsNo='TEST-RES-NEW-123456', ResSubId='1'),
            rec=dict(
                ResHotelId='4', ResGdsNo='TEST-RES-NEW-123456', ResMktSegment='OT', ResRoomCat='STDP',
                ResArrival=datetime.date(2022, 2, 21), ResDeparture=datetime.date(2022, 2, 25),
                Surname='CreateTester'),
            skip_live=True),
        dict(
            path='/res/delete',
            params=dict(
                ResHotelId='4', ResGdsNo='TEST-RES-NEW-123456', ResMktSegment='OT', ResRoomCat='STDP',
                ResArrival='2022-02-21', ResDeparture='2022-02-25', Surname='CreateTester', ResStatus='S'),
            json_values=dict(ErrorMessage="", ResHotelId='4', ResGdsNo='TEST-RES-NEW-123456', ResSubId='1'),
            rec=dict(
                ResHotelId='4', ResGdsNo='TEST-RES-NEW-123456', ResMktSegment='OT', ResRoomCat='STDP',
                ResArrival=datetime.date(2022, 2, 21), ResDeparture=datetime.date(2022, 2, 25),
                Surname='CreateTester', ResStatus='S'),
            skip_live=True),
        ]))
def test_write_services(path, params, status, json_values, rec, console_app_env):
    response = requests.post(path, json=params)
    print(response.url)
    assert response.status_code == status
    assert response.text.startswith("{")
    js = response.json()
    for k, v in json_values.items():
        assert js.get(k) == v
    ho_id = params['ResHotelId']
    gds_no = params['ResGdsNo']
    res_rec = ResFetch(console_app_env).fetch_by_gds_no(ho_id=ho_id, gds_no=gds_no)
    for k, v in rec.items():
        assert res_rec[k] == v


class ProxyNotWorkingTestRequestsConnection:
    def test_github_events(self, console_app_env):
        _ = self

        url = 'https://api.github.com/events'
        with_proxy = True
        if with_proxy:
            user = console_app_env.get_var('wsUser')
            password = console_app_env.get_var('wsPassword')
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
