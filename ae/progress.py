from ae.core import DEBUG_LEVEL_VERBOSE
from ae.console_app import ConsoleApp, _logger


class Progress:
    """ helper class for to easily display progress of long running tasks with several items on the console/log output.
    """
    def __init__(
            self, cae: ConsoleApp,
            start_counter: int = 0, total_count: int = 0,  # pass either start_counter or total_counter (not both)
            start_msg: str = "", next_msg: str = "",       # message templates/masks for start, processing and end
            end_msg: str = "Finished processing of {total_count} having {err_counter} failures:{err_msg}",
            err_msg: str = "{err_counter} errors on processing {total_count} items, current={run_counter}:{err_msg}",
            nothing_to_do_msg: str = ''):
        self.cae: ConsoleApp = cae          #: internal reference to the used :class:`console_app.ConsoleApp` instance
        if not next_msg and cae.get_option('debugLevel') >= DEBUG_LEVEL_VERBOSE:
            # default next message built only if >= DEBUG_LEVEL_VERBOSE
            next_msg = "Processing '{processed_id}': " + \
                       ("left" if start_counter > 0 and total_count == 0 else "item") + \
                       " {run_counter} of {total_count}. {err_counter} errors={err_msg}"

        def _complete_msg_prefix(msg, pch='#'):
            return (pch in msg and msg) or msg and " " + pch * 3 + "  " + msg or ""

        self._next_msg = _complete_msg_prefix(next_msg)
        self._end_msg = _complete_msg_prefix(end_msg)
        self._err_msg = _complete_msg_prefix(err_msg, '*')

        self._err_counter = 0
        self._run_counter = start_counter + 1  # def=decrementing run_counter
        self._total_count = start_counter
        self._delta = -1
        if total_count > 0:  # incrementing run_counter
            self._run_counter = 0
            self._total_count = total_count
            self._delta = 1
        elif start_counter <= 0:
            if nothing_to_do_msg:
                self.cae.uprint(_complete_msg_prefix(nothing_to_do_msg), logger=_logger)
            return  # RETURN -- empty set - nothing to process

        if start_msg:
            self.cae.uprint(_complete_msg_prefix(start_msg).format(run_counter=self._run_counter + self._delta,
                                                                   total_count=self._total_count), logger=_logger)

    def next(self, processed_id: str = '', error_msg: str = '', next_msg: str = ''):
        """ log the processing of the next item of this long-running task.

        :param processed_id:    id(s) of the next item (to be displayed on console/logging output).
        :param error_msg:       pass the error message to display if the next item produced any errors.
        :param next_msg:        message to output.
        """
        self._run_counter += self._delta
        if error_msg:
            self._err_counter += 1

        if error_msg and self._err_msg:
            self.cae.uprint(self._err_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                                 err_counter=self._err_counter, err_msg=error_msg,
                                                 processed_id=processed_id), logger=_logger)

        if not next_msg:
            next_msg = self._next_msg
        if next_msg:
            # using uprint with end parameter instead of leading \r will NOT GET DISPLAYED within PyCharm,
            # .. also not with flush - see http://stackoverflow.com/questions/34751441/
            # when-writing-carriage-return-to-a-pycharm-console-the-whole-line-is-deleted
            # .. uprint('   ', pend, end='\r', flush=True)
            next_msg = '\r' + next_msg
            self.cae.uprint(next_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                            err_counter=self._err_counter, err_msg=error_msg,
                                            processed_id=processed_id), logger=_logger)

    def finished(self, error_msg: str = ''):
        """ display end of processing for the current item.

        :param error_msg:   optional error message to display if current items produced any error.
        """
        if error_msg and self._err_msg:
            self.cae.uprint(self._err_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                                 err_counter=self._err_counter, err_msg=error_msg), logger=_logger)
        self.cae.uprint(self.get_end_message(error_msg=error_msg), logger=_logger)

    def get_end_message(self, error_msg: str = '') -> str:
        """ determine message text for finishing the currently processed item.

        :param error_msg:   optional error message to display if current items produced any error.
        :return:            message text for to display.
        """
        return self._end_msg.format(run_counter=self._run_counter, total_count=self._total_count,
                                    err_counter=self._err_counter, err_msg=error_msg)
