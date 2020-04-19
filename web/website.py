from otp import config

import asyncio
from aiohttp import web
import aiomysql

import hashlib

import logging

from Crypto.Cipher import AES

import json


SECRET = b'N)\x8fgj\x1a~\\\x1f\x1e\xa54\xc9\xd9\xf5\x83'

logging.basicConfig(level=logging.DEBUG)

table_creation = '''CREATE TABLE accounts (
    username VARCHAR(255) NOT NULL PRIMARY KEY UNIQUE,
    hash VARBINARY(255) NOT NULL,
    salt VARBINARY(64) NOT NULL,
    disl_id INT NOT NULL, 
    access ENUM('FULL', 'VELVET_ROPE') NOT NULL DEFAULT 'FULL',
    account_type ENUM('NO_PARENT_ACCOUNT', 'WITH_PARENT_ACCOUNT') NOT NULL DEFAULT 'NO_PARENT_ACCOUNT',
    create_friends_with_chat ENUM('YES', 'CODE', 'NO') NOT NULL DEFAULT 'YES',
    chat_code_creation_rule ENUM('YES', 'PARENT', 'NO') NOT NULL DEFAULT 'YES',
    whitelist_chat_enabled ENUM('YES', 'NO') NOT NULL DEFAULT  'YES'
);
'''


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


import os

INSTALL_FILES = {

}

patcher_info = []
required_install_files = []
file_versions = []

EXTRACT = 1
REQUIRED = 1 << 1
OPTIONAL = 1 << 2

DIR = os.path.join('web', 'content')


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
{patcher_info}
GAME_WHITELIST_URL={GAME_WHITELIST_URL}'''


async def handle_patcher(request):
    print(request.method, request.path, request.query_string)
    return web.Response(text=PATCHER_VER)


with open(os.path.join(DIR, 'twhitelist.dat'), 'r', encoding='windows-1252') as f:
    WHITELIST = f.read()


async def handle_whitelist(request):
    print(request.method, request.path, request.query_string)
    return web.Response(text=WHITELIST)


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
PATCHER_VERSION_STRING_SERVER=V1.0.1.47
'''

# BUTTON_2: TOP TOONS
# BUTTON_3: PLAYER'S GUIDE
# BUTTON_4: HOMEPAGE
# BUTTON_5: MANAGE ACCOUNT
# BUTTON_7: FORGOT PASSWORD
# BUTTON_8: NEW ACCOUNT
#


async def handle_start_show(request):
    print(request.method, request.path, request.query_string)

    return web.Response(text=PATCHER_STARTSHOW)


import re

username_pattern = re.compile(r'[A-za-z0-9_]+')


async def handle_login(request):
    print(request.method, request.path, request.query)

    username = request.query.get('n')

    if not username:
        return web.Response()

    if not username_pattern.match(username):
        return web.Response()

    password = request.query.get('p')

    if not password:
        return web.Response()

    if len(username) > 255:
        return web.Response()

    if len(password) > 255:
        return web.Response()

    print(f'{username} attempting to login...')

    async with await request.app['pool'].acquire() as conn:
        async with await conn.cursor(aiomysql.DictCursor) as cursor:
            try:
                await cursor.execute(f'SELECT * FROM accounts WHERE username=\'{username}\'')
                info = await cursor.fetchone()

                if not info:
                    print(f'Creating new account for {username}...')
                    info = await create_new_account(username, password, cursor)
            except Exception as e:
                print('error: ', e.args, e)

    request.app['pool'].release(conn)

    if not info:
        return web.Response()

    cmp_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), info['salt'], iterations=101337)

    if cmp_hash != info['hash']:
        print('hashes dont match', cmp_hash, info['hash'], len(info['hash']))
        return web.Response(text='LOGIN_ERROR=23')

    del info['hash']
    del info['salt']

    # Now make the token.

    cipher = AES.new(SECRET, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(json.dumps(info).encode('utf-8'))
    token = b''.join([cipher.nonce, tag, ciphertext])

    print(token)

    action = 'LOGIN_ACTION=PLAY'
    token = f'LOGIN_TOKEN={token.hex()}'
    username = f'GAME_USERNAME={username}'
    disl_id = f'GAME_DISL_ID={info["disl_id"]}'
    download_url = 'PANDA_DOWNLOAD_URL=http://127.0.0.1:8080/'
    account_url = 'ACCOUNT_SERVER=http://127.0.0.1/'
    is_test_svr = 'IS_TEST_SERVER=0'
    game_url = 'GAME_SERVER=127.0.0.1'
    acc_params = f'webAccountParams=&chatEligible=1&secretsNeedsParentPassword=0'
    whitelist_url = 'GAME_WHITELIST_URL=http://127.0.0.1:8080/'

    response ='\n'.join((action, token, username, disl_id, download_url, account_url, game_url,
                                        acc_params, is_test_svr, whitelist_url))

    print('sending reponse', response)

    return web.Response(text=response)


async def create_new_account(username: str, password: str, cursor: aiomysql.DictCursor):
    salt = os.urandom(56)
    accc_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations=101337)

    print('salt', 'hash', len(salt), len(accc_hash))

    salt = f"X'{salt.hex()}'"
    accc_hash = f"X'{accc_hash.hex()}'"

    try:
        await cursor.execute("USE otp; INSERT INTO objects (class_name) VALUES ('Account');")
        print('inserted')
        await cursor.execute("SELECT LAST_INSERT_ID();")
        do_id = (await cursor.fetchone())['LAST_INSERT_ID()']

        print('CREATED NEW ACCOUNT WITH ID: %s' % do_id)

        array = (0).to_bytes(4, 'little') * 6
        av_set = len(array).to_bytes(2, 'little') + array

        await cursor.execute(f"INSERT INTO account (do_id, DcObjectType, ACCOUNT_AV_SET, pirateAvatars) VALUES ({do_id}, 'Account', X'{av_set.hex()}', X'{av_set.hex()}');")
        await cursor.execute('USE web;')

        await cursor.execute(f"INSERT INTO accounts (username, hash, salt, disl_id) VALUES ('{username}', {accc_hash}, {salt}, {do_id});")
        await cursor.connection.commit()

        await cursor.execute(f"SELECT * FROM accounts WHERE username='{username}'")

    except Exception as e:
        print(e, e.__class__)

    return await cursor.fetchone()


async def init_app():
    app = web.Application()
    app.router.add_get('/patcher.ver', handle_patcher)
    app.router.add_get('/launcher/current/patcher.ver', handle_patcher)
    app.router.add_get('/twhitelist.dat', handle_whitelist)

    app.router.add_get('/launcher/current/patcher.startshow', handle_start_show)

    app.router.add_get('/login', handle_login)
    app.router.add_static('/', path='web/content/', name='releaseNotes.html')
    pool = await aiomysql.create_pool(host='127.0.0.1', port=3306, user='toontown', password='7i8k!aQ6PFj1', db='web', maxsize=5)

    async with await pool.acquire() as conn:
        async with await conn.cursor() as cursor:
            await cursor.execute('SHOW TABLES;')
            tables = await cursor.fetchone()
            if not tables or 'accounts' not in tables:
                await cursor.execute(table_creation)

    pool.release(conn)

    app['pool'] = pool

    print('init done')

    return app


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    print('running app..')
    web.run_app(app, host='127.0.0.1', port=8080)
    app['pool'].terminate()
    print('lll')


