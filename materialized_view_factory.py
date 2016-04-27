"""
The MIT License (MIT)

Copyright (c) 2016 Jeff Widman

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""
# materialized_view_factory.py
# example for use with Flask-SQLAlchemy

# Accompanying blog post:
# http://www.jeffwidman.com/blog/847/

# Many thanks to Mike Bayer (@zzzeek) for his help.

from sqlalchemy.ext import compiler
from sqlalchemy.schema import DDLElement
from app import db


class CreateMaterializedView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


@compiler.compiles(CreateMaterializedView)
def compile(element, compiler, **kw):
    # Could use "CREATE OR REPLACE MATERIALIZED VIEW..."
    # but I'd rather have noisy errors
    return 'CREATE MATERIALIZED VIEW %s AS %s' % (
        element.name,
        compiler.sql_compiler.process(element.selectable, literal_binds=True),
        )


def create_mat_view(name, selectable, metadata=db.metadata):
    _mt = db.MetaData() # temp metadata just for initial Table object creation
    t = db.Table(name, _mt) # the actual mat view class is bound to db.metadata
    for c in selectable.c:
        t.append_column(db.Column(c.name, c.type, primary_key=c.primary_key))
    db.event.listen(
        metadata, 'after_create',
        CreateMaterializedView(name, selectable)
        )

    @db.event.listens_for(metadata, 'after_create')
    def create_indexes(target, connection, **kw):
        for idx in t.indexes:
            idx.create(connection)

    db.event.listen(
        metadata, 'before_drop',
        db.DDL('DROP MATERIALIZED VIEW IF EXISTS ' + name)
        )
    return t


def refresh_mat_view(name, concurrently):
    # since session.execute() bypasses autoflush, must manually flush in order
    # to include newly-created/modified objects in the refresh
    db.session.flush()
    _con = 'CONCURRENTLY ' if concurrently else ''
    db.session.execute('REFRESH MATERIALIZED VIEW ' + _con + name)


def refresh_all_mat_views(concurrently=True):
    '''Refreshes all materialized views. Currently, views are refreshed in
    non-deterministic order, so view definitions can't depend on each other.'''
    # TODO use `include='materialized'` once https://bitbucket.org/zzzeek/sqlalchemy/issues/3588/ lands
    mat_views = db.inspect(db.engine).get_view_names()
    for v in mat_views:
        refresh_mat_view(v, concurrently)


class MaterializedView(db.Model):
    __abstract__ = True

    @classmethod
    def refresh(cls, concurrently=True):
        '''Refreshes the current materialized view'''
        refresh_mat_view(cls.__table__.fullname, concurrently)
