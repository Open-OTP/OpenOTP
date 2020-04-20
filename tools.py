from Crypto.Cipher import Blowfish
from Crypto.Hash import SHA1
from Crypto.Protocol.KDF import PBKDF2

# This is the key used by Disney to encrypt their configs.
DISNEY_PASSWORD = "t@@V'[T'bm"


iteration_factor = 1000


def decrypt_configrc(password, in_path, out_path=None):
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
        decrypted = cipher.decrypt(ciphertext)

        if out_path is None:
            print(decrypted)
        else:
            with open(out_path, 'wb+') as of:
                of.write(decrypted)


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


def sign_prc(in_path):
    with open(in_path, 'r') as f:
        data = f.read()

    key = RSA.generate(1024)
    public_key = key.publickey().export_key()
    priv_key = key.export_key()

    row_width = 64
    h = SHA1.new(data.encode('utf-8'))
    sig = pkcs1_15.new(key).sign(h)
    from textwrap import wrap
    sig_lines = [f'##!sig {l}' for l in wrap(sig.hex(), row_width)]
    sig = '\n'.join(sig_lines)

    return public_key, priv_key, sig
