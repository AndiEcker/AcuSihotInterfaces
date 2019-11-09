from ae.console import ConsoleApp
from ae_notification.notification import add_notification_options, init_notification
from ae.db_ora import OraDb
from sys_data_acu import add_ac_options

__version__ = '0.1'

cae = ConsoleApp("Test connectivity to SMTP and Acumen/Oracle servers")

add_ac_options(cae)
add_notification_options(cae)

cae.po('SMTP Uri/From/To:', cae.get_opt('smtpServerUri'), cae.get_opt('smtpFrom'), cae.get_opt('smtpTo'))
cae.po('Acumen Usr/DSN:', cae.get_opt('acuUser'), cae.get_opt('acuDSN'))


notification, _ = init_notification(cae, 'TestConnectivity')

notification.send_notification('test message from Sihot server')


ora_db = OraDb(cae, dict(User=cae.get_opt('acuUser'), Password=cae.get_opt('acuPassword'),
                         DSN=cae.get_opt('acuDSN')))
err_msg = ora_db.connect()
if err_msg:
    cae.po(err_msg)
    notification.send_notification(err_msg, subject="OraDb Acumen connect error")
    cae.shutdown(1)

err_msg = ora_db.select('dual', ['sysdate'])
if err_msg:
    cae.po(err_msg)
    notification.send_notification(err_msg, subject="OraDb Acumen select error")
    cae.shutdown(2)

cae.po(str(ora_db.fetch_value()))

ora_db.close()

cae.shutdown()
