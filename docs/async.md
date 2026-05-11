# Async support

SQLAlchemy-History supports SQLAlchemy's async ORM as long as versioning is configured
with `support_async=True`.

```python
>>> from sqlalchemy_history import make_versioned
>>> make_versioned(user_cls=None, options={"support_async": True})
```

## Complete example

```python
import asyncio

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, configure_mappers

from sqlalchemy_history import make_versioned, version_class

make_versioned(user_cls=None, options={"support_async": True})


class Base(DeclarativeBase):
    pass


class Article(Base):
    __versioned__ = {}
    __tablename__ = "article"
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.Unicode(255))
    content = sa.Column(sa.UnicodeText)


async def main():
    configure_mappers()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    ArticleVersion = version_class(Article)

    async with Session() as session:
        article = Article(name="Some article", content="Some content")
        session.add(article)
        await session.commit()

        versions = (await session.scalars(article.versions.select())).all()
        print(versions[0].name)  # 'Some article'

        article.name = "Updated article"
        await session.commit()

        latest_version = await session.scalar(
            sa
            .select(ArticleVersion)
            .where(ArticleVersion.id == article.id)
            .order_by(ArticleVersion.transaction_id.desc())
            .limit(1)
        )
        print(latest_version.name)  # 'Updated article'

    await engine.dispose()


asyncio.run(main())
```

## Loading versions

When `support_async=True`, SQLAlchemy-History configures the parent `.versions`
relationship with SQLAlchemy's `write_only` loader. This means you should load
versions with a `select()` statement instead of indexing into the collection.

```python
>>> import sqlalchemy as sa
>>> versions = (await session.scalars(article.versions.select())).all()
>>> first_version = versions[0]
```

Direct history queries also use normal SQLAlchemy 2.x async patterns:

```python
>>> import sqlalchemy as sa
>>> from sqlalchemy_history import version_class
>>> ArticleVersion = version_class(Article)
>>> versions = (
...     await session.scalars(
...         sa.select(ArticleVersion).where(ArticleVersion.name == "Some article")
...     )
... ).all()
```

## Reverting updates

Reverting a version is still synchronous at the Python level. It mutates ORM state
immediately, and you persist the reverted state with `await session.commit()`.

```python
>>> import sqlalchemy as sa
>>> versions = (await session.scalars(article.versions.select())).all()
>>> original_version = versions[0]
>>> article.name = "Updated article"
>>> await session.commit()
>>> original_version.revert()
>>> await session.commit()
>>> article.name
'Some article'
```

## Reverting deleted rows

```python
>>> import sqlalchemy as sa
>>> article = Article(name="Some article", content="Some content")
>>> session.add(article)
>>> await session.commit()
>>> version = (await session.scalars(article.versions.select())).first()
>>> await session.delete(article)
>>> await session.commit()
>>> version.revert()
>>> await session.commit()
>>> restored = await session.scalar(sa.select(Article).where(Article.id == article.id))
>>> restored is not None
True
```

## Reverting relationships

Relationship revert works the same way in async sessions. Load the historical version,
call `revert(relations=[...])`, and commit the changes.

```python
>>> import sqlalchemy as sa
>>> class Tag(Base):
...     __tablename__ = "tag"
...     __versioned__ = {}
...     id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
...     name = sa.Column(sa.Unicode(255))
...     article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
...     article = sa.orm.relationship(Article, backref="tags")
...
>>> article = Article(
...     name="Some article",
...     tags=[Tag(name="Good"), Tag(name="Interesting")]
... )
>>> session.add(article)
>>> await session.commit()
>>> tag = await session.scalar(sa.select(Tag).where(Tag.name == "Interesting"))
>>> await session.delete(tag)
>>> await session.commit()
>>> first_version = (await session.scalars(article.versions.select())).first()
>>> first_version.revert(relations=["tags"])
>>> await session.commit()
```
