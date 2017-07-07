from sfif import SfInterface


class TestSfInterface:
    def test_all_contacts(self, console_app_env):
        si = SfInterface(username=console_app_env.get_config('sfSandboxUser'),
                         password=console_app_env.get_config('sfPassword'),
                         token=console_app_env.get_config('sfToken'),
                         sandbox=True)
        for c in si.contacts_with_rci_id():
            print(c)
            assert len(c) == 3  # tuple items: (Id, CD_CODE, (RCI refs))
            assert len(c[0]) == 18
            assert len(c[2]) > 0
