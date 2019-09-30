from ae.console import ConsoleApp
from ae.progress import Progress


class TestProgress:
    def test_init_start_msg(self, capsys, restore_app_env):
        msg = "msg_text"
        erm = "t_err_msg"
        cae = ConsoleApp("test_progress_init_start")
        progress = Progress(cae, total_count=1, start_msg=msg, nothing_to_do_msg=msg)
        progress.finished(error_msg=erm)
        out, err = capsys.readouterr()
        assert msg in out
        assert erm in out
        assert err == ""

    def test_init_nothing_to_do(self, capsys, restore_app_env):
        msg = "msg_text"
        erm = "test_error_msg"
        cae = ConsoleApp("test_progress_init_ntd")
        progress = Progress(cae, nothing_to_do_msg=msg)
        progress.next(error_msg=erm)
        out, err = capsys.readouterr()
        assert msg in out
        assert erm in out
        assert err == ""

    def test_end_msg(self, capsys, restore_app_env):
        msg = "msg_text"
        cae = ConsoleApp("test_progress_init_end")
        progress = Progress(cae, end_msg=msg)
        progress.next()
        progress.finished()
        assert msg in progress.get_end_message()
        out, err = capsys.readouterr()
        assert msg in out
        assert err == ""

    def test_start_msg_placeholders(self, capsys, restore_app_env):
        msg = "start_msg_text"
        phm = "{run_counter} of {total_count}"
        cae = ConsoleApp("test_progress_start_msg")
        progress = Progress(cae, total_count=1, start_msg=msg + phm)
        progress.finished()
        out, err = capsys.readouterr()
        assert msg in out
        assert phm not in out
        assert err == ""

    def test_end_msg_placeholders(self, capsys, restore_app_env):
        msg = "end_msg_text"
        phm = " {run_counter} of {total_count} has {err_counter} errors: {err_msg}"
        cae = ConsoleApp("test_progress_end_msg")
        progress = Progress(cae, total_count=1, end_msg=msg + phm)
        progress.finished()
        out, err = capsys.readouterr()
        assert msg in out
        assert phm not in out
        assert err == ""

    def test_next_and_err_msg_placeholders(self, capsys, restore_app_env):
        msg = "next_msg_text"
        erm = "err_msg_text"
        phm = "{run_counter} of {total_count} {err_counter} errs {err_msg}"
        cae = ConsoleApp("test_progress_next_msg")
        progress = Progress(cae, next_msg=msg + phm, err_msg=erm + phm)
        progress.next(error_msg="error message init in Progress.__init__")
        out, err = capsys.readouterr()
        assert msg not in out       # this is because next message starts with \r and does not get captured
        assert erm in out
        assert phm not in out
        assert err == ""
