SysDataMan.exe -D=1 --pull="shC{'filter_records': lambda r: not r.val('Phone'), 'field_names': ['Phone']" --push="asC{'filter_records': lambda r: r.val('Phone')}" --assDSN=ass_cache@tf-sh-sihot1v.acumen.es -L=log\PullShPhoneIfEmpty.log