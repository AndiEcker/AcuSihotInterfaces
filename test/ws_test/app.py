"""
After setting up mod_wsgi using embedded mode (instead of daemon mode) the apache/linux server configs are used.

to change the encoding charsets in embedded mode you could change the environment variables
LANG and LC_ALL of apache in /etc/apache2/envvars. Following the recommendations of the main developer of mod_wsgi
(see http://blog.dscpl.com.au/2014/09/setting-lang-and-lcall-when-using.html) it would be better and saver
to run mod_wsgi in daemon mode and specify there the language and locale settings by adding to the apache .conf file:

    WSGIDaemonProcess my-site lang='en_US.UTF-8' locale='en_US.UTF-8'

More useful hints and workarounds for common mod_wsgi issues and configuration problems you find here:
    https://code.google.com/archive/p/modwsgi/wikis/ApplicationIssues.wiki
Newer version:
    https://modwsgi.readthedocs.io/en/develop/user-guides/application-issues.html

"""

# change working dir so bottle.py will be find by next import statement (also for relative paths and template lookup)
import os
import sys
import locale
startup_cwd = os.getcwd()
os.chdir(os.path.dirname(__file__))
sys.path.append(os.path.dirname(__file__))

import cx_Oracle
import psycopg2

from bottle import default_app, request, template, html_escape

# app and application will be used when used as server plug-in in apache/nginx
app = application = default_app()


MISSING_ATTR = '*#ERR#*'
HDR = 'HEADER_MARKER'


@app.route('/<name>')
def show_index(name):
    return template("hello {{}}", name=name)


@app.route('/')
def show_index():
    tb = "\n<table>"
    th1 = "<thead><tr><th>"
    th2 = "</th></tr></thead><tbody>"
    tr1 = "\n<tr><td>"
    tc = "</td><td>"
    tr2 = "</td></tr>"
    te = "\n</tbody></table>\n"

    ps = list()

    ps.append(("Request Attributes", HDR))
    ps.append(("url", request.url))
    ps.append(("app", request.app))
    ps.append(("route", request.route))
    ps.append(("remote_addr", request.remote_addr))
    ps.append(("remote_route", request.remote_route))
    ps.append(("url_args", request.url_args))
    ps.append(("path", request.path))
    ps.append(("method", request.method))
    ps.append(("files", request.files))
    ps.append(("json", request.json))
    ps.append(("chunked", request.chunked))
    ps.append(("fullpath", request.fullpath))
    ps.append(("query_string", request.query_string))
    ps.append(("script_name", request.script_name))
    ps.append(("content_type", request.content_type))
    ps.append(("content_length", request.content_length))
    ps.append(("is_xhr/ajax", request.is_xhr))
    ps.append(("auth", request.auth))
    ps.append(("body", request.body))

    ps.append(("Request WSGI Environment", HDR))
    ps += [(k, v) for k, v in request.environ.items()]

    ps.append(("Request Params", HDR))
    ps += [(k, v) for k, v in request.params.items()]

    ps.append(("Request Headers", HDR))
    ps += [(k, v) for k, v in request.headers.items()]

    ps.append(("Cookies", HDR))
    ps += [(k, v) for k, v in request.cookies.items()]

    ps += append_sys_environ()

    ph = [(te + tb + th1 if str(c) == HDR else tr1) + t + (th2 if str(c) == HDR else tc + html_escape(str(c)) + tr2)
          for t, c in ps]

    return tb + th1 + "".join(ph)[len(te + tb + th1):] + te


def append_sys_environ():
    ps = list()
    ps.append(("System Environment", HDR))
    ps.append(("python version", sys.version))
    ps.append(("default locale", locale.getdefaultlocale()))
    ps.append(("preferred encoding", locale.getpreferredencoding()))
    ps.append(("default encoding", sys.getdefaultencoding()))
    ps.append(("file encoding", sys.getfilesystemencoding()))
    ps.append(("stdout", str(sys.stdout) + sys.stdout.errors))
    ps.append(("stderr", str(sys.stderr) + sys.stderr.errors))
    ps.append(("argv", sys.argv))
    ps.append(("executable", sys.executable))
    ps.append(("cwd", os.getcwd()))
    ps.append(("cwd@startup", startup_cwd))
    ps.append(("__file__ ", __file__))
    ps.append(("frozen", getattr(sys, 'frozen', False)))
    if getattr(sys, 'frozen', False):
        ps.append(("bundle-dir", getattr(sys, '_MEIPASS', MISSING_ATTR)))

    ps.append(("System Environment Variables", HDR))
    ps += [_ for _ in sorted(os.environ.items())]

    ps.append(("Oracle Database Environment", HDR))
    ps.append(("__version__", cx_Oracle.__version__))
    ps.append(("version", cx_Oracle.version))
    ps.append(("clientversion()", cx_Oracle.clientversion()))

    ps.append(("Postgres Database Environment", HDR))
    ps.append(("__version__", psycopg2.__version__))
    ps.append(("__libpq_version__", getattr(psycopg2, "__libpq_version__", MISSING_ATTR)))  # available in V 2.7+
    ps.append(("apilevel", psycopg2.apilevel))

    return ps


if __name__ == '__main__':      # for debugging at least show sys environment (not depending on bottle.request)
    print("\n".join([l + '\t:' + str(v).replace(HDR, '====================') for l, v in append_sys_environ()]))
