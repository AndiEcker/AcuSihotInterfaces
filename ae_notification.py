from smtplib import SMTP  # , SMTP_SSL
from email.mime.text import MIMEText

from ae_console_app import uprint, DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE


class Notification:
    def __init__(self, smtp_server_uri, mail_from, mail_to, local_mail_host='', used_system='', mail_body_footer='',
                 debug_level=DEBUG_LEVEL_DISABLED):
        if debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint(' ###  New Notification({}, {}, {}, {}, {}).'
                   .format(smtp_server_uri, mail_from, mail_to, local_mail_host, used_system))
        # split smtp server URI into host, user, pw and port
        if '@' in smtp_server_uri:    # [user[:password]@]mail_server_host[:mail_server_port]
            pos = smtp_server_uri.rindex('@')
            user_info = smtp_server_uri[:pos]
            mail_host = smtp_server_uri[pos + 1:]
            if ':' in user_info:
                pos = user_info.index(':')
                self._user_name = user_info[:pos]
                self._user_password = user_info[pos + 1:]
            else:
                self._user_name = user_info
                self._user_password = ''
        else:
            mail_host = smtp_server_uri
        if ':' in mail_host:
            pos = mail_host.rindex(':')
            self._mail_host = mail_host[:pos]
            self._mail_port = int(mail_host[pos + 1:])
        else:
            self._mail_host = mail_host
            self._mail_port = 25    # use default SMTP port 25, or use port 587 for E-SMTP
        self._local_mail_host = local_mail_host if local_mail_host else self._mail_host

        self._mail_from = mail_from
        self._mail_to = mail_to
        self._used_system = used_system
        self._mail_body_footer = mail_body_footer
        self.debug_level = debug_level

    def send_notification(self, msg_body, subject=None, mail_to=None, data_dict=None):
        if self._mail_body_footer:
            msg_body += '\n' + self._mail_body_footer
        if not subject:
            subject = 'Notification'
        if self._used_system:
            subject += ' [' + self._used_system + ']'
        if not mail_to:
            mail_to = self._mail_to
        if isinstance(mail_to, str):
            mail_to_expr = mail_to
            try:
                mail_to = eval(mail_to_expr)  # data_dict for to check data, subject/msg_body for to mail content
            except Exception as ex:
                uprint(" **** Notification.send_notification() exception '" + str(ex) +
                       "' on evaluating of expression '" + str(mail_to_expr) +
                       "' with subject='" + subject + "' and data_dict='" + str(data_dict) + "'.")
        if not isinstance(mail_to, list):
            uprint(" **** Notification.send_notification(): invalid email-to address list or expression '" +
                   str(mail_to) + "' - using ITDevmen fallback!")
            mail_to = ['ITDevmen@acumen.es']

        # log error message and try to send it per email
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint(' #### Notification.send_notification(): "{}" with subject "{}".'.format(msg_body, subject))
        err_msg = ''
        try:
            message = MIMEText(msg_body)
            message['Subject'] = subject
            message['From'] = self._mail_from
            message['To'] = ', '.join(mail_to)
            # Oracle P_SENDMAIL() is using smtp server as local host
            # SMTP_SSL always throws "SSL:UNKNOWN_PROTOCOL" error: with (SMTP_SSL if self._mail_port == 587 else SMTP)\
            with SMTP(self._mail_host, self._mail_port, local_hostname=self._local_mail_host) as s:
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    s.set_debuglevel(1)
                s.ehlo()
                # using s.starttls() is throwing error "STARTTLS extension not supported by server."
                # s.starttls()
                s.login(self._user_name, self._user_password)
                unreached_recipients = s.send_message(message, self._mail_from, mail_to)
                if unreached_recipients:
                    err_msg = 'Unreached Recipients: ' + str(unreached_recipients)
        except Exception as mex:
            err_msg = 'mail send exception: {}'.format(mex)

        if err_msg and self.debug_level >= DEBUG_LEVEL_ENABLED:
            uprint(' **** Notification.send_notification() error: {}.'.format(err_msg))

        return err_msg
