# Queries

You can query history models just like any other sqlalchemy declarative model.

```python
>>> from sqlalchemy_history import version_class
>>> ArticleVersion = version_class(Article)
>>> session.query(ArticleVersion).filter_by(name=u'some name').all()
```

## How many transactions have been executed?

```python
>>> from sqlalchemy_history import transaction_class
>>> Transaction = transaction_class(Article)
>>> Transaction.query.count()
```

## Querying for entities of a class at a given revision

In the following example we find all articles which were affected by transaction 33.

```python
>>> session.query(ArticleVersion).filter_by(transaction_id=33)
```


## Querying for transactions, at which entities of a given class changed

In this example we find all transactions which affected any instance of 'Article' model. This query needs the TransactionChangesPlugin.

```python
>>> TransactionChanges = Article.__versioned__['transaction_changes']
>>> entries = (
...     session.query(Transaction)
...     .innerjoin(Transaction.changes)
...     .filter(
...         TransactionChanges.entity_name.in_(['Article'])
...     )
... )
```


## Querying for versions of entity that modified given property


In the following example we want to find all versions of Article class which changed the attribute 'name'. This example assumes you are using
PropertyModTrackerPlugin.

```python
>>> ArticleVersion = version_class(Article)
>>> session.query(ArticleHistory).filter(ArticleVersion.name_mod).all()
```