"""
Progress Of Long Running Processes
==================================

This module is simplifying the display of progress messages for long running processes on
the command console/shell of your OS.


Basic Usage
-----------

For to display the progress of a long running process at your console/shell you first have to
create an instance of the :class:`Progress` class. The first argument that need to be specified
in this instantiation is the instance of your application class (either :class:`~ae.core.AppBase`,
:class:`~ae.core.SubApp` or :class:`~ae.console.ConsoleApp`). Additionally the number of items
to be processed in the long running process could be specified with the :paramref:`~Progress.total_count`
keyword argument::

    progress = Progress(app, total_count=number_of_items_to_be_processed)

Then your process has to call the :meth:`~Progress.next` method for each processed item of your
long running process. And if the process is finished you can request to print an end-message by
calling the :meth:`~Progress.finished` method of your :class:`Progress` instance::

    while process_is_not_finished:
        progress.next()
    progress.finished()

The above code snippets are printing a start message to your console at the instantiation of :class:`Progress`.
Then every call of the method :meth:`~Progress.next` will print the next message and finally the method
:meth:`~Progress.finished` will print an end message onto your console when the long running process
is finished.


Individual Message Templates
----------------------------


Message Template Placeholders
-----------------------------
.
start message   : {run_counter} {total_count}


Integrated Error Notification
-----------------------------




"""
from ae.core import AppBase, _logger


class Progress:
    """ helper class for to easily display progress of long running tasks with several items on the console/log output.
    """
    def __init__(
            self, app_base: AppBase,
            start_counter: int = 0, total_count: int = 0,  # pass either start_counter or total_counter (not both)
            start_msg: str = "", next_msg: str = "",       # message templates/masks for start, processing and end
            end_msg: str = "Finished processing of {total_count} having {err_counter} failures:{err_msg}",
            err_msg: str = "{err_counter} errors on processing {total_count} items, current={run_counter}:{err_msg}",
            nothing_to_do_msg: str = ''):
        """ prepare print-outs for a new progress (long running process with incrementing or decrementing item counter).

        :param app_base:            instance of an application class.
        :param start_counter:       decrementing counter (until zero is reached) if :paramref:`~Progress.total_count`
                                    got not passed or got passed with a value of zero or below zero.
                                    start counter value of an incrementing counter if you passed the number of
                                    items to the argument :paramref:`~Progress.total_count`.
        :param total_count:         number of items that will be processed with an incrementing counter.
        :param start_msg:           optional start message template with placeholders.
        :param next_msg:            optional next message - if an empty string get passed then a default message
                                    will be provided with placeholders - pass None if you want to suppress the
                                    print-out of a next message.
        :param end_msg:             end message template with placeholders, pass None if you want to suppress the
                                    print-out of an end message (in this case only a new line will be printed).
        :param err_msg:             error message template with placeholders.
        :param nothing_to_do_msg:   optional message template printed-out if the values of the two arguments
                                    :paramref:`~Progress.start_counter` and :paramref:`~Progress.total_count` are
                                    less or equal to zero.
        """
        self.app_base: AppBase = app_base   #: reference attribute to the used :class:`core.AppBase` instance
        if next_msg == "":
            next_msg = "Processing '{processed_id}': " + \
                       ("left" if start_counter > 0 and total_count == 0 else "item") + \
                       " {run_counter} of {total_count}. {err_counter} errors:{err_msg}"

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
            self._run_counter = start_counter
            self._total_count = total_count
            self._delta = 1
        elif start_counter <= 0:
            if nothing_to_do_msg:
                self.app_base.po(_complete_msg_prefix(nothing_to_do_msg), logger=_logger)
            return  # RETURN -- empty set - nothing to process

        if start_msg:
            self.app_base.po(_complete_msg_prefix(start_msg).format(run_counter=self._run_counter + self._delta,
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

        params = dict(run_counter=self._run_counter, total_count=self._total_count, processed_id=processed_id,
                      err_counter=self._err_counter, err_msg=error_msg)
        if error_msg and self._err_msg:
            self.app_base.po(self._err_msg.format(**params), logger=_logger)

        if not next_msg:
            next_msg = self._next_msg
        if next_msg:
            # using print_out()/po() with end parameter instead of leading \r will NOT GET DISPLAYED within PyCharm,
            # .. also not with flush - see http://stackoverflow.com/questions/34751441/
            # when-writing-carriage-return-to-a-pycharm-console-the-whole-line-is-deleted
            # .. po('   ', pend, end='\r', flush=True)
            next_msg = '\r' + next_msg
            self.app_base.po(next_msg.format(**params), logger=_logger)

    def finished(self, processed_id: str = '', error_msg: str = ''):
        """ display end of processing for the current item.

        :param processed_id:    id(s) of the next item (to be displayed on console/logging output).
        :param error_msg:       optional error message to display if current items produced any error.
        """
        if error_msg and self._err_msg:
            self.app_base.po(self._err_msg.format(
                run_counter=self._run_counter, total_count=self._total_count, processed_id=processed_id,
                err_counter=self._err_counter, err_msg=error_msg),
                             logger=_logger)
        self.app_base.po(self.get_end_message(error_msg=error_msg), logger=_logger)

    def get_end_message(self, processed_id: str = '', error_msg: str = '') -> str:
        """ determine message text for finishing the currently processed item.

        :param processed_id:    id(s) of the next item (to be displayed on console/logging output).
        :param error_msg:       optional error message to display if current items produced any error.
        :return:                message text for to display.
        """
        return self._end_msg.format(
            run_counter=self._run_counter, total_count=self._total_count, processed_id=processed_id,
            err_counter=self._err_counter, err_msg=error_msg)
