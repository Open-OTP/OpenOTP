import unittest

from otp.networking import DownstreamClient, OTPProtocol


class TestProtocol(OTPProtocol):
    pass


class TestClient(DownstreamClient):
    upstream_protocol = TestProtocol


class TestMessageDirector(unittest.TestCase):
    pass



if __name__ == '__main__':
    unittest.main()
