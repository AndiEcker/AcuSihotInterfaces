from ae.console_app import ConsoleApp, uprint
from ae.notification import add_notification_options, init_notification
from ae.db import OraDB
from acif import add_ac_options

__version__ = '0.1'

cae = ConsoleApp(__version__, "Test connectivity to SMTP and Acumen/Oracle servers")

add_ac_options(cae)
add_notification_options(cae)

uprint('SMTP Uri/From/To:', cae.get_option('smtpServerUri'), cae.get_option('smtpFrom'), cae.get_option('smtpTo'))
uprint('Acumen Usr/DSN:', cae.get_option('acuUser'), cae.get_option('acuDSN'))


notification, _ = init_notification(cae, 'TestConnectivity')

notification.send_notification('test message from Sihot server')


ora_db = OraDB(dict(User=cae.get_option('acuUser'), Password=cae.get_option('acuPassword'),
                    DSN=cae.get_option('acuDSN')),
               app_name=cae.app_name(), debug_level=cae.get_option('debugLevel'))
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
