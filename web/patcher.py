from otp import config
import os
import hashlib

INSTALL_FILES = {

}

patcher_info = []
required_install_files = []
file_versions = []

EXTRACT = 1
REQUIRED = 1 << 1
OPTIONAL = 1 << 2
DIR = config['WebServer.CONTENT_DIR']


def get_file_info(fn):
    file_hash = hashlib.md5()

    buffer = 4096

    with open(fn, 'rb') as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(0, 0)

        while f.tell() != size:
            file_hash.update(f.read(buffer))

    return size, file_hash.digest().hex()


for fn in os.listdir(DIR):
    if not fn.startswith('phase'):
        continue
    fp = os.path.join(DIR, fn)
    size, file_hash = get_file_info(fp)

    INSTALL_FILES[fn] = (size, file_hash)

    patcher_info.append(f'FILE_{fn}.v1.0.0={size} {file_hash}')
    required_install_files.append(f'{fn}:{REQUIRED}')
    file_versions.append(f'FILE_{fn}.current=v1.0.0')

patcher_info = "\n".join(patcher_info)
file_versions = "\n".join(file_versions)

GAME_WHITELIST_URL = 'http://127.0.0.1:8080/'
LOGIN_API_URL = 'http://127.0.0.1:8080/login'

PATCHER_VER = f'''REQUIRED_INSTALL_FILES={" ".join(required_install_files)}
{file_versions}
{patcher_info}'''

PATCHER_STARTSHOW = f'''
GLOBAL_URL_1=http://127.0.0.1:8080/releaseNotes.html
GLOBAL_URL_2=http://127.0.0.1:8080/
GLOBAL_URL_3=http://disney.go.com/toontown/launcher/live/install/LoadMoviePC.html
BUTTON_2=http://127.0.0.1:8080/
BUTTON_3=http://127.0.0.1:8080/
BUTTON_4=http://127.0.0.1:8080/
BUTTON_5=http://127.0.0.1:8080/
BUTTON_7=http://127.0.0.1:8080/
BUTTON_8=http://127.0.0.1:8080/
WEB_PAGE_LOGIN_RPC={LOGIN_API_URL}
PATCHER_VERSION_STRING_SERVER=V1.0.1.47'''
