from ae.console import ConsoleApp
from ae.progress import Progress


class TestProgress:
    def test_init_start_msg(self, capsys, restore_app_env):
        msg = 'msg_text'
        erm = 't_err_msg'
        cae = ConsoleApp('test_progress_init')
        progress = Progress(cae, total_count=1, start_msg=msg, nothing_to_do_msg=msg)
        progress.finished(error_msg=erm)
        out, err = capsys.readouterr()
        assert msg in out
        assert erm in out
        assert err == ""

    def test_init_nothing_to_do(self, capsys, restore_app_env):
        msg = 'msg_text'
        erm = 'test_error_msg'
        cae = ConsoleApp('test_progress_init')
        progress = Progress(cae, nothing_to_do_msg=msg)
        progress.next(error_msg=erm)
        out, err = capsys.readouterr()
        assert msg in out
        assert erm in out
        assert err == ""

    def test_end_msg(self, capsys, restore_app_env):
        msg = 'msg_text'
        cae = ConsoleApp('test_progress_init')
        progress = Progress(cae, end_msg=msg)
        progress.next()
        progress.finished()
        assert msg in progress.get_end_message()
        out, err = capsys.readouterr()
        assert msg in out
        assert err == ""
