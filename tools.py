from Crypto.Cipher import Blowfish
from Crypto.Hash import SHA1
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


# This is the key used by Disney to encrypt their configs.
DISNEY_PASSWORD = "t@@V'[T'bm"


iteration_factor = 1000


def decrypt_configrc(in_path, out_path=None, password=DISNEY_PASSWORD):
    with open(in_path, 'rb') as f:
        cipher_id = int.from_bytes(f.read(2), 'little', signed=False)
        key_length = int.from_bytes(f.read(2), 'little', signed=False)
        count = int.from_bytes(f.read(2), 'little', signed=False)

        if cipher_id == 91:
            # BF-CBC
            cipher = Blowfish
            mode = Blowfish.MODE_CBC
        else:
            raise ValueError('unknown cipher id: %s' % cipher_id)

        block_size = cipher.block_size

        iv = f.read(block_size)
        ciphertext = f.read()

        key = PBKDF2(password, iv, key_length, count * iteration_factor + 1, hmac_hash_module=SHA1)

        cipher = cipher.new(key, mode, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), block_size)

        if out_path is None:
            print(decrypted)
        else:
            with open(out_path, 'wb+') as of:
                of.write(decrypted)


def encrypt_configrc(in_path: str, out_path: str, password: str, iterations: int, key_length=16, cipher_id=91):
    if cipher_id == 91:
        # BF-CBC
        cipher = Blowfish
        mode = Blowfish.MODE_CBC
    else:
        raise ValueError('unknown cipher id: %s' % cipher_id)

    block_size = cipher.block_size
    iv = get_random_bytes(block_size)
    key = PBKDF2(password, iv, key_length, iterations * iteration_factor + 1, hmac_hash_module=SHA1)

    with open(in_path, 'rb') as f:
        data = f.read()

    cipher = cipher.new(key, mode, iv)
    ciphertext = cipher.encrypt(pad(data, block_size))

    with open(out_path, 'wb+') as f:
        f.write(cipher_id.to_bytes(2, 'little', signed=False))
        f.write(key_length.to_bytes(2, 'little', signed=False))
        f.write(iterations.to_bytes(2, 'little', signed=False))
        f.write(iv)
        f.write(ciphertext)


from Crypto.Signature import pkcs1_15
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA1


# PRC Key from libdtoolconfig
prc_key = '''-----BEGIN PUBLIC KEY-----
MIGdMA0GCSqGSIb3DQEBAQUAA4GLADCBhwKBgQDYmxPo0pzu8Hh+teHp7neMZy0G
JQMqEZ/Pdj/26eVTyDXL7YknLbn1QpDjyhv2PyQcXMcUoLTEA9k7o3sdRKWNFtD9
e9fOcIj4ZmhInllIpkDIWt1hmsRFZCHnzG+ie+9Rq2xfsTToIqvX3Yu88BNtVNfY
2ielPQzKTsArZWIwkQIBBw==
-----END PUBLIC KEY-----
'''


def check_prc_sig(in_path):
    signature = bytearray()

    h = SHA1.new()

    with open(in_path, 'r') as f:
        lines = f.readlines()

        for line in lines:
            if line.startswith('##!sig '):
                signature.extend(bytes.fromhex(line[7:]))
            else:
                h.update(line.encode('utf-8'))

    try:
        pkey = RSA.import_key(prc_key)
        pkcs1_15.new(pkey).verify(h, signature)
    except (ValueError, TypeError):
        return False

    return True


def sign_prc(in_path, out_path, key_path):
    with open(key_path, 'rb') as kf:
        key = RSA.import_key(kf.read())

    with open(in_path, 'rb') as in_cfg:
        data = in_cfg.read()

    if not data[-1] == b'\n':
        data += b'\n'

    data += b'##!\n'

    row_width = 64
    h = SHA1.new(data)
    sig = pkcs1_15.new(key).sign(h)
    from textwrap import wrap
    sig_lines = [f'##!sig {l}' for l in wrap(sig.hex(), row_width)]
    sig = '\n'.join(sig_lines)
    with open(out_path, 'wb+') as out_cfg:
        out_cfg.write(data)
        out_cfg.write(sig.encode('utf-8'))


def overwrite_prc_key(dll_path, key_path):
    with open(key_path, 'rb') as f:
        pub_key = f.read()

    with open(dll_path, 'rb+') as f:
        f.seek(0x7F0E8)
        f.write(pub_key)


def get_prc_key(dll_path):
    with open(dll_path, 'rb') as f:
        f.seek(0x7F0E8)
        return f.read(271)


# Example
# overwrite_prc_key('libdtoolconfig.dll', 'prc.pub')
# sign_prc('decrypted2.prc', 'signed.prc', 'prc.priv')
# encrypt_configrc('signed.prc', '../2013/ToontownOnline/Configrc.pre', DISNEY_PASSWORD, 100)
