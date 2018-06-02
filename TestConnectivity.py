from ae_console_app import ConsoleApp, uprint
from ae_notification import add_notification_options, init_notification
from ae_db import OraDB
from acif import ACU_DEF_USR, ACU_DEF_DSN

__version__ = '0.1'

cae = ConsoleApp(__version__, "Test connectivity to SMTP and Acumen/Oracle servers")

cae.add_option('acuUser', "User name of Acumen/Oracle system", ACU_DEF_USR, 'u')
cae.add_option('acuPassword', "User account password on Acumen/Oracle system", '', 'p')
cae.add_option('acuDSN', "Data source name of the Acumen/Oracle database system", ACU_DEF_DSN, 'd')
add_notification_options(cae)

uprint('SMTP Uri/From/To:', cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), cae.get_option('acuDSN'))


notification, _ = init_notification(cae, 'TestConnectivity')

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
