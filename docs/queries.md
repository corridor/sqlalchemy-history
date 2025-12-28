# Queries

You can query history models just like any other sqlalchemy declarative model.

```python
>>> from sqlalchemy_history import version_class
>>> import sqlalchemy as sa
>>> ArticleVersion = version_class(Article)
>>> session.scalars(sa.select(ArticleVersion).filter_by(name=u'some name')).all()
```

## How many transactions have been executed?

```python
>>> from sqlalchemy_history import transaction_class
>>> import sqlalchemy as sa
>>> Transaction = transaction_class(Article)
>>> session.scalar(sa.select(sa.func.count()).select_from(Transaction))
```

## Querying for entities of a class at a given revision

In the following example we find all articles which were affected by transaction 33.

```python
>>> session.scalars(sa.select(ArticleVersion).filter_by(transaction_id=33)).all()
```

## Querying for transactions, at which entities of a given class changed

In this example we find all transactions which affected any instance of 'Article' model. This query needs the TransactionChangesPlugin.

```python
>>> TransactionChanges = Article.__versioned__['transaction_changes']
>>> statement = (
...     sa.select(Transaction)
...     .join(Transaction.changes)
...     .where(
...         TransactionChanges.entity_name.in_(['Article'])
...     )
... )
... entries = session.scalars(statement).all()
```

## Querying for versions of entity that modified given property

In the following example we want to find all versions of Article class which changed the attribute 'name'. This example assumes you are using
PropertyModTrackerPlugin.

```python
>>> ArticleVersion = version_class(Article)
>>> session.scalars(sa.select(ArticleHistory).filter(ArticleVersion.name_mod)).all()
```
