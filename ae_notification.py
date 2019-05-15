from smtplib import SMTP, SMTP_SSL
from email.mime.text import MIMEText

from sys_data_ids import DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_ENABLED, DEBUG_LEVEL_VERBOSE
from ae_console_app import uprint


DEF_ENC_PORT = 25
DEF_ENC_SERVICE_NAME = 'smtp'
SSL_ENC_PORT = 465
SSL_ENC_SERVICE_NAME = 'smtps'
TSL_ENC_PORT = 587
TSL_ENC_SERVICE_NAME = 'smtpTLS'

MAX_LEN_BODY_IN_LOG = 159       # max number of characters of the send mail body that get passed to the log file


def add_notification_options(cae, add_warnings=False):
    cae.add_option('smtpServerUri', "SMTP notification server account URI [user[:pw]@]host[:port]", '', 'c')
    cae.add_option('smtpFrom', "SMTP sender/from address", '', 'f')
    cae.add_option('smtpTo', "List/Expression of SMTP receiver/to addresses", list(), 'r')
    if add_warnings:
        # separate warnings email is optional for some applications (e.g. AcuServer)
        cae.add_option('warningsMailToAddr', "Warnings SMTP receiver addresses (if differs from smtpTo)", list(), 'v')


def init_notification(cae, system_name=''):
    notification = warning_notification_emails = None
    if cae.get_option('smtpServerUri') and cae.get_option('smtpFrom') and cae.get_option('smtpTo'):
        notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                                    mail_from=cae.get_option('smtpFrom'),
                                    mail_to=cae.get_option('smtpTo'),
                                    used_system=system_name or cae.app_name(),
                                    debug_level=cae.get_option('debugLevel'))
        uprint("SMTP Uri/From/To:", cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'),
               cae.get_option('smtpTo'))
        warning_notification_emails = cae.get_option('warningsMailToAddr')
        if warning_notification_emails:
            uprint("Warnings SMTP receiver address(es):", warning_notification_emails)
    return notification, warning_notification_emails


class Notification:
    def __init__(self, smtp_server_uri, mail_from, mail_to, local_mail_host='', used_system='', mail_body_footer='',
                 debug_level=DEBUG_LEVEL_DISABLED):
        if debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint(' ###  New Notification({}, {}, {}, {}, {}, {}).'
                   .format(smtp_server_uri, mail_from, mail_to, local_mail_host, used_system, mail_body_footer))
        # split smtp server URI into service, host, user, pw and port (all apart host are optional)
        if '://' in smtp_server_uri:
            self._mail_service, smtp_server_uri = smtp_server_uri.split('://')
        else:
            self._mail_service = DEF_ENC_SERVICE_NAME
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
            self._user_name = ''
            self._user_password = ''
        if ':' in mail_host:
            pos = mail_host.rindex(':')
            self._mail_host = mail_host[:pos]
            self._mail_port = int(mail_host[pos + 1:])
        else:
            self._mail_host = mail_host
            # default SMTP port: 25/DEF_ENC_PORT, port 587/TSL_ENC_PORT for E-SMTP/TLS or 465/SSL_ENC_PORT for smtps/SSL
            self._mail_port = SSL_ENC_PORT if self._mail_service == SSL_ENC_SERVICE_NAME \
                else (TSL_ENC_PORT if self._mail_service == TSL_ENC_SERVICE_NAME else DEF_ENC_PORT)
        self._local_mail_host = local_mail_host or self._mail_host

        self._mail_from = mail_from
        self._mail_to = mail_to
        self._used_system = used_system
        self._mail_body_footer = mail_body_footer
        self.debug_level = debug_level

    def send_notification(self, msg_body='', subject=None, mail_to=None, data_dict=None, body_style=''):
        """
        send a notification email

        :param msg_body: email body text (including \n for new lines)
        :param subject: email subject text (optional, default="Notification")
        :param mail_to: list of email receiver addresses (optional: default=instance/self mail_to addresses)
        :param data_dict: dict of additional data used for to display and for to evaluate mail_to expression (optional)
        :param body_style: mime text body style (optional, def='html' if '</' in msg_body else 'plain')
        :return: error message on error or empty string if notification got send successfully
        """
        if self._mail_body_footer:
            msg_body += '\n' + self._mail_body_footer
        if not subject:
            subject = 'Notification'
        if self._used_system:
            subject += ' [' + self._used_system + ']'
        if not mail_to:
            mail_to = self._mail_to
        title_ext = " with subject='" + subject + "'" + \
                    (" and data_dict='" + str(data_dict) + "'" if data_dict else "") + "."
        if isinstance(mail_to, str):
            mail_to_expr = mail_to
            try:
                mail_to = eval(mail_to_expr)  # data_dict for to check data, subject/msg_body for to mail content
            except Exception as ex:
                uprint(" **** Notification.send_notification() exception '" + str(ex) +
                       "' on evaluating of expression '" + str(mail_to_expr) +
                       "'" + title_ext)
        if not isinstance(mail_to, list):
            uprint(" **** Notification.send_notification(): invalid email-to address list or expression '" +
                   str(mail_to) + "' - using ITDevmen fallback!")
            mail_to = ['ITDevmen@signallia.com']
        body_style = body_style or 'html' if '</' in msg_body else 'plain'
        if body_style == 'html':
            # using the <pre>...</pre> tags we no longer need replace(' ', '&nbsp;')
            msg_body = str(msg_body).replace('\r\n', '<br>').replace('\n', '<br>').replace('\r', '<br>')
            # adding html special char conversion disables all other html tags too:
            #    .replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>') \
            #    .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # log error message and try to send it per email
        if self.debug_level >= DEBUG_LEVEL_VERBOSE:
            uprint(" #### Notification.send_notification(): BODY{" + msg_body[:MAX_LEN_BODY_IN_LOG] + "..}" + title_ext)
        err_msg = ''
        try:
            message = MIMEText(msg_body, _subtype=body_style)
            message['Subject'] = subject
            message['From'] = self._mail_from
            message['To'] = ', '.join(mail_to)
            # Oracle P_SENDMAIL() is using smtp server as local host
            # SMTP_SSL could throw "SSL:UNKNOWN_PROTOCOL" error
            conn_type = SMTP_SSL if self._mail_port == SSL_ENC_PORT or self._mail_service == SSL_ENC_SERVICE_NAME \
                else SMTP
            with conn_type(self._mail_host, self._mail_port, local_hostname=self._local_mail_host) as s:
                # if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                #    s.set_debuglevel(1)
                s.ehlo()
                # using s.starttls() could throwing error "STARTTLS extension not supported by server."
                if self._mail_service == TSL_ENC_SERVICE_NAME:
                    s.starttls()
                if self._user_name:
                    s.login(self._user_name, self._user_password)
                unreached_recipients = s.send_message(message, self._mail_from, mail_to)
                if unreached_recipients:
                    err_msg = 'Unreached Recipients: ' + str(unreached_recipients)
        except Exception as mex:
            err_msg = 'mail send exception: {}'.format(mex)

        if err_msg and self.debug_level >= DEBUG_LEVEL_ENABLED:
            uprint(' **** Notification.send_notification() error: {}.'.format(err_msg))

        return err_msg
