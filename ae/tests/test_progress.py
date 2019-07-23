from ae.console_app import ConsoleApp
from ae.progress import Progress


class TestProgress:
    def test_init_start_msg(self):
        msg = 'msg_text'
        cae = ConsoleApp('0.0', 'test_progress_init')
        progress = Progress(cae, total_count=1, start_msg=msg, nothing_to_do_msg=msg)
        progress.finished(error_msg='t_err_msg')

    def test_init_nothing_to_do(self):
        msg = 'msg_text'
        cae = ConsoleApp('0.0', 'test_progress_init')
        progress = Progress(cae, nothing_to_do_msg=msg)
        progress.next(error_msg='test_error_msg')
