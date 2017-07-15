from sfif import SfInterface
from acu_sf_sh_sys_data import EXT_REFS_SEP


class TestSfInterface:
    def test_all_contacts(self, console_app_env):
        si = SfInterface(username=console_app_env.get_config('sfSandboxUser')
                         if console_app_env.get_option('debugLevel') >= 2 else console_app_env.get_config('sfUser'),
                         password=console_app_env.get_config('sfPassword'),
                         token=console_app_env.get_config('sfToken'),
                         sandbox=True)
        assert si.error_msg == ""
        for c in si.contacts_with_rci_id(EXT_REFS_SEP):
            print(c)
            assert len(c) == 5  # tuple items: (CD_CODE, Sf_Id, Sihot_Guest_Object_Id, (RCI refs), is_owner)
            assert len(c[1]) == 18
            assert len(c[3]) > 0
        assert si.error_msg == ""
