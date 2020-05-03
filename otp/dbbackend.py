from otp import config

import aiomysql
from typing import Tuple, List
import warnings
from .exceptions import *


class DatabaseBackend:
    def __init__(self, service):
        self.service = service
        self.dc = self.service.dc

    async def setup(self):
        raise NotImplementedError

    async def create_object(self, dclass, fields: Tuple[Tuple[str, bytes]]):
        raise NotImplementedError

    def query_object_all(self, do_id: int):
        raise NotImplementedError

    def query_object_fields(self, do_id: int, fields):
        raise NotImplementedError

    def set_field(self, do_id: int, field: str, value: bytes):
        raise NotImplementedError

    def set_fields(self, do_id: int, fields: Tuple[Tuple[str, bytes]]):
        raise NotImplementedError


class SQLBackend(DatabaseBackend):
    def __init__(self, service):
        DatabaseBackend.__init__(self, service)
        self.pool = None

    async def setup(self):
        self.pool = await aiomysql.create_pool(host=config['SQL.HOST'], port=config['SQL.PORT'], user=config['SQL.USER'],
                                               password=config['SQL.PASSWORD'], loop=self.service.loop, db='otp', maxsize=5)
        conn = await self.pool.acquire()
        cursor = await conn.cursor()

        warnings.filterwarnings('ignore', 'Table \'[A-Za-z]+\' already exists')

        await cursor.execute('SHOW TABLES LIKE \'objects\';')
        if await cursor.fetchone() is None:
            await cursor.execute('CREATE TABLE objects (do_id INT NOT NULL AUTO_INCREMENT, class_name VARCHAR(255), PRIMARY KEY (do_id));')
            await cursor.execute("ALTER TABLE objects AUTO_INCREMENT = %d;" % self.service.min_channel)

        for dclass in self.dc.classes:
            if 'DcObjectType' not in dclass.fields_by_name:
                continue

            columns = []
            for field in dclass.inherited_fields:
                if field.is_db:
                    columns.append(f'{field.name} blob,')

            if not columns:
                continue

            columns = ''.join(columns)
            cmd = f'CREATE TABLE IF NOT EXISTS {dclass.name} (do_id INT, {columns} PRIMARY KEY (do_id), FOREIGN KEY (do_id) REFERENCES objects(do_id));'
            await cursor.execute(cmd)

        await cursor.close()
        conn.close()
        self.pool.release(conn)

    async def _query_dclass(self, conn: aiomysql.Connection, do_id: int) -> str:
        cursor = await conn.cursor()
        await cursor.execute(f'SELECT class_name FROM objects WHERE do_id={do_id}')
        await conn.commit()
        dclass_name = await cursor.fetchone()
        await cursor.close()

        if dclass_name is None:
            conn.close()
            self.pool.release(conn)
            raise OTPQueryNotFound('object %d not found' % do_id)

        return dclass_name[0]

    async def create_object(self, dclass, fields: List[Tuple[str, bytes]]):
        # TODO: get field default from DC and pack
        columns = [field[0] for field in fields]
        values = ["X'%s'" % field[1].hex().upper() for field in fields]

        for field in dclass.inherited_fields:
            if field.is_db and field.is_required:
                if field.name not in columns:
                    raise OTPCreateFailed('Missing required db field: %s' % field.name)

        columns = ', '.join(columns)
        values = ', '.join(values)

        conn = await self.pool.acquire()
        cursor = await conn.cursor()

        cmd = f"INSERT INTO objects (class_name) VALUES ('{dclass.name}');"
        try:
            await cursor.execute(cmd)
            await conn.commit()
        except aiomysql.IntegrityError as e:
            await cursor.close()
            conn.close()
            self.pool.release(conn)
            raise OTPCreateFailed('Created failed with error code: %s' % e.args[0])

        await cursor.execute('SELECT LAST_INSERT_ID();')
        do_id = (await cursor.fetchone())[0]

        cmd = f'INSERT INTO {dclass.name} (do_id, DcObjectType, {columns}) VALUES ({do_id}, \'{dclass.name}\', {values});'

        try:
            await cursor.execute(cmd)
            await conn.commit()
        except aiomysql.IntegrityError as e:
            await cursor.close()
            conn.close()
            self.pool.release(conn)
            raise OTPCreateFailed('Created failed with error code: %s' % e.args[0])

        await cursor.close()
        conn.close()
        self.pool.release(conn)
        return do_id

    async def query_object_all(self, do_id, dclass_name=None):
        conn = await self.pool.acquire()

        if dclass_name is None:
            dclass_name = await self._query_dclass(conn, do_id)

        cursor = await conn.cursor(aiomysql.DictCursor)
        try:
            await cursor.execute(f'SELECT * FROM {dclass_name} WHERE do_id={do_id}')
        except aiomysql.ProgrammingError:
            await cursor.close()
            conn.close()
            raise OTPQueryFailed('Tried to query with invalid dclass name: %s' % dclass_name)

        fields = await cursor.fetchone()
        await cursor.close()

        conn.close()
        self.pool.release(conn)

        return fields

    async def query_object_fields(self, do_id, field_names, dclass_name=None):
        conn = await self.pool.acquire()

        if dclass_name is None:
            dclass_name = await self._query_dclass(conn, do_id)

        field_names = ", ".join(field_names)

        cursor = await conn.cursor(aiomysql.DictCursor)
        await cursor.execute(f'SELECT {field_names} FROM {dclass_name} WHERE do_id={do_id}')
        values = await cursor.fetchone()
        await cursor.close()
        conn.close()
        self.pool.release(conn)

        return values

    async def set_field(self, do_id, field_name, value, dclass_name=None):
        conn = await self.pool.acquire()

        if dclass_name is None:
            dclass_name = await self._query_dclass(conn, do_id)

        cursor = await conn.cursor()

        value = f"X'{value.hex().upper()}'"

        try:
            await cursor.execute(f'UPDATE {dclass_name} SET {field_name} = {value} WHERE do_id={do_id}')
            await conn.commit()
        except aiomysql.IntegrityError as e:
            await cursor.close()
            conn.close()
            self.pool.release(conn)
            raise OTPQueryFailed('Query failed with error code: %s' % e.args[0])

        await cursor.close()
        conn.close()
        self.pool.release(conn)

    async def set_fields(self, do_id, fields, dclass_name=None):
        conn = await self.pool.acquire()

        if dclass_name is None:
            dclass_name = await self._query_dclass(conn, do_id)

        cursor = await conn.cursor()

        items = ', '.join((f"{field_name} = X'{value.hex().upper()}'" for field_name, value in fields))

        try:
            await cursor.execute(f'UPDATE {dclass_name} SET {items} WHERE do_id={do_id}')
            await conn.commit()
        except aiomysql.IntegrityError as e:
            await cursor.close()
            conn.close()
            self.pool.release(conn)
            raise OTPQueryFailed('Query failed with error code: %s' % e.args[0])

        await cursor.close()
        conn.close()
        self.pool.release(conn)
