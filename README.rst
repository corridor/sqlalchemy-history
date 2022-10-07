SQLAlchemy-History
==================

|Build Status| |Version Status|

Auditing extension for sqlalchemy which keeps a track of the history of your sqlalchemy models

Features
--------

- Supports sqlalchemy 1.4+ and python 3.6+
- Tracks history for inserts, deletes, and updates
- Does not store updates which don't change anything
- Supports alembic migrations
- Can revert objects data as well as all object relations at given transaction even if the object was deleted
- Transactions can be queried afterwards using SQLAlchemy query syntax
- Query for changed records at given transaction
- Temporal relationship reflection. Get the relationships of an object in that point in time.


QuickStart
----------

::


    pip install sqlalchemy-history



In order to make your models versioned you need two things:

1. Call make_versioned() before your models are defined.
2. Add __versioned__ to all models you wish to add versioning to


.. code-block:: python


    from sqlalchemy_history import make_versioned


    make_versioned(user_cls=None)


    class Article(Base):
        __versioned__ = {}
        __tablename__ = 'article'

        id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
        name = sa.Column(sa.Unicode(255))
        content = sa.Column(sa.UnicodeText)


    article = Article(name='Some article', content='Some content')
    session.add(article)
    session.commit()

    # article has now one version stored in database
    article.versions[0].name
    # 'Some article'

    article.name = 'Updated name'
    session.commit()

    article.versions[1].name
    # 'Updated name'


    # lets revert back to first version
    article.versions[0].revert()

    article.name
    # 'Some article'

For completeness, below is a working example.

.. code-block:: python

    from sqlalchemy_history import make_versioned
    from sqlalchemy import Column, Integer, Unicode, UnicodeText, create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import create_session, configure_mappers

    make_versioned(user_cls=None)

    Base = declarative_base()
    class Article(Base):
        __versioned__ = {}
        __tablename__ = 'article'
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(Unicode(255))
        content = Column(UnicodeText)

    configure_mappers()
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    session = create_session(bind=engine, autocommit=False)

    article = Article(name=u'Some article', content=u'Some content')
    session.add(article)
    session.commit()
    article.versions[0].name
    article.name = u'Updated name'
    session.commit()
    article.versions[1].name
    article.versions[0].revert()
    article.name

Resources
---------

- `Documentation <https://sqlalchemy-continuum.readthedocs.io/>`_
- `Issue Tracker <http://github.com/corridor/sqlalchemy-history/issues>`_
- `Code <http://github.com/corridor/sqlalchemy-history/>`_

.. |Build Status| image:: https://github.com/corridor/sqlalchemy-history/workflows/Test/badge.svg
   :target: https://github.com/corridor/sqlalchemy-history/actions?query=workflow%3ATest
.. |Version Status| image:: https://img.shields.io/pypi/v/sqlalchemy-history.png
   :target: https://pypi.python.org/pypi/sqlalchemy-history/


More information
----------------

- http://en.wikipedia.org/wiki/Slowly_changing_dimension
- http://en.wikipedia.org/wiki/Change_data_capture
- http://en.wikipedia.org/wiki/Anchor_Modeling
- http://en.wikipedia.org/wiki/Shadow_table
- https://wiki.postgresql.org/wiki/Audit_trigger
- https://wiki.postgresql.org/wiki/Audit_trigger_91plus
- http://kosalads.blogspot.fi/2014/06/implement-audit-functionality-in.html
- https://github.com/2ndQuadrant/pgaudit


Comparison
----------

Primary reasons to create another library:

 - Be future looking and support sqlalchemy 1.4 and 2.x
 - Support multiple databases (sqlite, mysql, postgres, mssql, oracle)
 - Focus on the history tracking and be as efficient as possible when doing it

We found multiple libraries which has an implementation of history tracking:

- `sqlalchemy-continuum <https://github.com/kvesteri/sqlalchemy-continuum>`_
    - Does not support oracle, mssql
    - Feature filled making it difficult to maintain all plugins/extensions
- `flask-continuum <https://github.com/bprinty/flask-continuum>`_
    - Thin wrapper on sqlalchemy-continuum specifically for flask
- `postgresql-audit <https://github.com/kvesteri/postgresql-audit>`_
    - Supports only postgres
- `versionalchemy <https://github.com/NerdWalletOSS/versionalchemy>`_
    - Not updated in a while
    - No reverting capability, Relationship queries on history not available
- `django-simple-history <https://github.com/jazzband/django-simple-history>`_
    - Uses django ORM, does not support sqlalchemy
- `sqlalchemy example versioning-objects <http://docs.sqlalchemy.org/en/latest/orm/examples.html#versioning-objects>`_
    - Simple example to demonstrate implementation - but very minimal
