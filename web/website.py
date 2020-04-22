from otp import config

import asyncio
from aiohttp import web
import aiomysql

import hashlib

import logging

from Crypto.Cipher import AES

import json


import os


SECRET = bytes.fromhex(config['General.LOGIN_SECRET'])

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

DEFAULT_ACCOUNT = {
    'ACCOUNT_AV_SET': (24).to_bytes(2, 'little') + (0).to_bytes(4, 'little') * 6,
    'pirateAvatars': b'\x00\x00',
    'HOUSE_ID_SET': b'\x00\x00',
    'ESTATE_ID': b'\x00\x00\x00\x00',
    'ACCOUNT_AV_SET_DEL': b'\x00\x00',
    'PLAYED_MINUTES': b'\x00\x00',
    'PLAYED_MINUTES_PERIOD': b'\x00\x00',
    'CREATED': b'\x00\x00',
    'LAST_LOGIN': b'\x00\x00',
}


DIR = config['WebServer.CONTENT_DIR']
PATCHER_VER_FILE = os.path.join(DIR, 'patcher.ver')
PATCHER_STARTSHOW_FILE = os.path.join(DIR, 'patcher.startshow')
HOST = config['WebServer.HOST']
PORT = config['WebServer.PORT']


if config['WebServer.WRITE_PATCH_FILES']:
    print('Writing patcher files...')
    from . import patcher

    with open(PATCHER_VER_FILE, 'w+') as f:
        f.write(patcher.PATCHER_VER)
    with open(PATCHER_STARTSHOW_FILE, 'w+') as f:
        f.write(patcher.PATCHER_STARTSHOW)


async def handle_patcher(request):
    print(request.method, request.path, request.query_string)
    return web.FileResponse(PATCHER_VER_FILE)


async def handle_start_show(request):
    print(request.method, request.path, request.query_string)

    return web.FileResponse(PATCHER_STARTSHOW_FILE)


with open(os.path.join(DIR, 'twhitelist.dat'), 'r', encoding='windows-1252') as f:
    WHITELIST = f.read()


async def handle_whitelist(request):
    print(request.method, request.path, request.query_string)
    return web.Response(text=WHITELIST)



# BUTTON_2: TOP TOONS
# BUTTON_3: PLAYER'S GUIDE
# BUTTON_4: HOMEPAGE
# BUTTON_5: MANAGE ACCOUNT
# BUTTON_7: FORGOT PASSWORD
# BUTTON_8: NEW ACCOUNT
#



import re

username_pattern = re.compile(r'[A-Za-z0-9_]+')
password_pattern = re.compile(r'[A-Za-z0-9_!@#$%^&*]+')


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

    if not password_pattern.match(password):
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
        return web.Response()

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
    download_url = f'PANDA_DOWNLOAD_URL=http://{HOST}:{PORT}/'
    account_url = f'ACCOUNT_SERVER=http://{HOST}:{PORT}/'
    is_test_svr = 'IS_TEST_SERVER=0'
    game_url = f'GAME_SERVER={config["ClientAgent.HOST"]}'
    acc_params = f'webAccountParams=&chatEligible=1&secretsNeedsParentPassword=0'
    whitelist_url = f'GAME_WHITELIST_URL=http://{HOST}:{PORT}'

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

        fields = list(DEFAULT_ACCOUNT.items())

        keys = ','.join((field[0] for field in fields))
        values = ','.join((f"X'{field[1].hex()}'" for field in fields))
        cmd = f"INSERT INTO account (do_id, DcObjectType, {keys}) VALUES ({do_id}, 'Account', {values});"
        print(cmd)
        await cursor.execute(cmd)
        await cursor.execute('USE web;')

        await cursor.execute(f"INSERT INTO accounts (username, hash, salt, disl_id) VALUES ('{username}', {accc_hash}, {salt}, {do_id});")
        await cursor.connection.commit()

        await cursor.execute(f"SELECT * FROM accounts WHERE username='{username}'")

    except Exception as e:
        print(e, e.__class__)

    return await cursor.fetchone()


async def handle_auth_delete(request):
    print(request.method, request.path, request.query, request.headers)
    args = await request.post()
    username, password = args.get('n'), args.get('p')

    if not username:
        return web.Response()

    if not username_pattern.match(username):
        return web.Response()

    if not password:
        return web.Response()

    if not password_pattern.match(password):
        return web.Response()

    if len(username) > 255:
        return web.Response()

    if len(password) > 255:
        return web.Response()

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
        return web.Response(text='ACCOUNT SERVER RESPONSE\n\nerrorCode=20\nerrorMsg=bad password')

    return web.Response(text='ACCOUNT SERVER RESPONSE')


async def init_app():
    app = web.Application()
    app.router.add_get('/patcher.ver', handle_patcher)
    app.router.add_get('/launcher/current/patcher.ver', handle_patcher)
    app.router.add_get('/twhitelist.dat', handle_whitelist)

    app.router.add_get('/launcher/current/patcher.startshow', handle_start_show)

    app.router.add_get('/login', handle_login)
    app.router.add_static('/', path=config['WebServer.CONTENT_DIR'], name='releaseNotes.html')

    app.router.add_post('/api/authDelete', handle_auth_delete)

    pool = await aiomysql.create_pool(host=config['SQL.HOST'], port=config['SQL.PORT'], user=config['SQL.USER'],
                                      password=config['SQL.PASSWORD'], db='web', maxsize=5)

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
    web.run_app(app, host=HOST, port=PORT)
    app['pool'].terminate()


