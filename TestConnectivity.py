from ae_console_app import ConsoleApp, uprint
from ae_db import OraDB, DEF_USER, DEF_DSN
from ae_notification import Notification

__version__ = '0.1'

cae = ConsoleApp(__version__, "Test connectivity to SMTP and Acumen/Oracle servers")

cae.add_option('smtpServerUri', "SMTP server URI [user[:pw]@]host[:port]", '', 'c')
cae.add_option('smtpFrom', "SMTP Sender/From address", '', 'f')
cae.add_option('smtpTo', "List/Expression of SMTP Receiver/To addresses", [], 'r')

cae.add_option('acuUser', "User name of Acumen/Oracle system", DEF_USER, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", DEF_DSN, 'd')

uprint('SMTP Uri/From/To:', cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), cae.get_option('acuDSN'))


notification = Notification(smtp_server_uri=cae.get_option('smtpServerUri'),
                            mail_from=cae.get_option('smtpFrom'),
                            mail_to=cae.get_option('smtpTo'),
                            used_system='TestConnectivity',
                            debug_level=2)

notification.send_notification('test message from Sihot server')


ora_db = OraDB(cae.get_option('acuUser'), cae.get_option('acuPassword'), cae.get_option('acuDSN'),
               debug_level=cae.get_option('debugLevel'))
err_msg = ora_db.connect()
if err_msg:
    uprint(err_msg)
    notification.send_notification(err_msg, subject="OraDB Acumen connect error")
    cae.shutdown(1)

err_msg = ora_db.select('dual', ['sysdate'])
if err_msg:
    uprint(err_msg)
    notification.send_notification(err_msg, subject="OraDB Acumen select error")
    cae.shutdown(2)

uprint(str(ora_db.fetch_value()))

ora_db.close()

cae.shutdown()
