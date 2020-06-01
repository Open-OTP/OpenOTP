# OpenOTP

OpenOTP is a Python 3 asyncio-based OTP for the Toontown Online 2013 client.
The goal of this project is to allow an unmodified original launcher and client to play the game.
The AI server is rewritten from scratch to take advantage of Python 3 features and allow the code to be more readable.



## Python Dependencies
* [pydc](https://github.com/alexanderr/pydc)
* [lark](https://github.com/lark-parser/lark)
* [uvloop](https://github.com/MagicStack/uvloop) (optional)
* aiohttp


## Database Backends
Currently only MySQL is supported. More database backends will be added in the future.


## How to setup:
* The OTP cluster can be ran through the `otp.otp` module.
* The AI server can be ran through the `ai.AIStart` module.
* The python web server can be ran through the `web.website` module. This is required to enable login through the original launcher.
* Currently, `ttconn`, a SSL proxy, is required to be built in order to use the original _unmodified_ client.