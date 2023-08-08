[![Coverage Status](https://coveralls.io/repos/github/corridor/sqlalchemy-history/badge.svg)](https://coveralls.io/github/corridor/sqlalchemy-history)

# SQLAlchemy-History

SQLAlchemy-history is a fork of sqlalchemy-continuum.
An auditing extension for sqlalchemy which keeps a track of the history of your sqlalchemy models

## Features

- Supports sqlalchemy 1.4+ and python 3.6+
- Tracks history for inserts, deletes, and updates
- Does not store updates which don't change anything
- Supports alembic migrations
- Can revert objects data as well as all object relations at given transaction even if the object was deleted
- Transactions can be queried afterwards using SQLAlchemy query syntax
- Query for changed records at given transaction
- Temporal relationship reflection. Get the relationships of an object in that point in time.

## QuickStart

```sh
pip install sqlalchemy-history
```

In order to make your models versioned you need two things:

1. Call `make_versioned()` before your models are defined.
2. Add `__versioned__` to all models you wish to add versioning to

```python
>>> from sqlalchemy_history import make_versioned
>>> make_versioned(user_cls=None)
>>> class Article(Base):
...    __versioned__ = {}
...    __tablename__ = 'article'
...    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
...    name = sa.Column(sa.Unicode(255))
...    content = sa.Column(sa.UnicodeText)
>>> article = Article(name='Some article', content='Some content')
>>> session.add(article)
>>> session.commit()
'article has now one version stored in database'
>>> article.versions[0].name
'Some article'
>>> article.name = 'Updated name'
>>> session.commit()
>>> article.versions[1].name
'Updated name'
>>> article.versions[0].revert()
'lets revert back to first version'
>>> article.name
'Some article'
```

For completeness, below is a working example.

```python
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
article = Article(name='Some article', content='Some content')
session.add(article)
session.commit()
print(article.versions[0].name) # 'Some article'
article.name = 'Updated name'
session.commit()
print(article.versions[1].name) # 'Updated name'
article.versions[0].revert()
print(article.name) # 'Some article'
```

## Resources

- [Documentation](https://sqlalchemy-continuum.readthedocs.io/)
- [Issue Tracker](http://github.com/corridor/sqlalchemy-history/issues)
- [Code](http://github.com/corridor/sqlalchemy-history/)

## More information

- [http://en.wikipedia.org/wiki/Slowly_changing_dimension](http://en.wikipedia.org/wiki/Slowly_changing_dimension)
- [http://en.wikipedia.org/wiki/Change_data_capture](http://en.wikipedia.org/wiki/Change_data_capture)
- [http://en.wikipedia.org/wiki/Anchor_Modeling](http://en.wikipedia.org/wiki/Anchor_Modeling)
- [http://en.wikipedia.org/wiki/Shadow_table](http://en.wikipedia.org/wiki/Shadow_table)
- [https://wiki.postgresql.org/wiki/Audit_trigger](https://wiki.postgresql.org/wiki/Audit_trigger)
- [https://wiki.postgresql.org/wiki/Audit_trigger_91plus](https://wiki.postgresql.org/wiki/Audit_trigger_91plus)
- [http://kosalads.blogspot.fi/2014/06/implement-audit-functionality-in.html](http://kosalads.blogspot.fi/2014/06/implement-audit-functionality-in.html)
- [https://github.com/2ndQuadrant/pgaudit](https://github.com/2ndQuadrant/pgaudit)

## Comparison

Primary reasons to create another library:

- Be future looking and support sqlalchemy 1.4 and 2.x
- Support multiple databases (sqlite, mysql, postgres, mssql, oracle)
- Focus on the history tracking and be as efficient as possible when doing it

We found multiple libraries which has an implementation of history tracking:

1. [sqlalchemy-continuum](https://github.com/kvesteri/sqlalchemy-continuum)
   - Does not support oracle, mssql
   - Feature filled making it difficult to maintain all plugins/extensions
2. [flask-continuum](https://github.com/bprinty/flask-continuum)
   - Thin wrapper on sqlalchemy-continuum specifically for flask
3. [postgresql-audit](https://github.com/kvesteri/postgresql-audit)
   - Supports only postgres
4. [versionalchemy](https://github.com/NerdWalletOSS/versionalchemy)
   - Not updated in a while
   - No reverting capability, Relationship queries on history not available
5. [django-simple-history](https://github.com/jazzband/django-simple-history)
   - Uses django ORM, does not support sqlalchemy
6. [sqlalchemy example versioning-objects](http://docs.sqlalchemy.org/en/latest/orm/examples.html#versioning-objects)
   - Simple example to demonstrate implementation - but very minimal
