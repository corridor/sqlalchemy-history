# Transactions

## Transaction


For each committed transaction SQLAlchemy-History creates a new Transaction record.

Transaction can be queried just like any other sqlalchemy declarative model.

```python
>>> from sqlalchemy_history import transaction_class
>>> Transaction = transaction_class(Article)
>>> session.query(Transaction).all() # find all transactions
```

## UnitOfWork

For each database connection SQLAlchemy-History creates an internal UnitOfWork object.
Normally these objects are created at before flush phase of session workflow. However you can also
force create unit of work before this phase.

```python
>>> uow = versioning_manager.unit_of_work(session)
```

Transaction objects are normally created automatically at before flush phase. If you need access
to transaction object before the flush phase begins you can do so by calling the create_transaction method
of the UnitOfWork class.

```python
>>> transaction = uow.create_transaction(session)
```

The version objects are normally created during the after flush phase but you can also force create those at any time by
calling make_versions method.


```python
>>> uow.make_versions(session)
```

## Workflow internals

Consider the following code snippet where we create a new article.

```python
>>> article = Article()
>>> article.name = u'Some article'
>>> article.content = u'Some content'
>>> session.add(article)
>>> session.commit()
```
This would execute the following SQL queries (on PostgreSQL)

```sql
1. INSERT INTO article (name, content) VALUES (?, ?)
    params: ('Some article', 'Some content')
2. INSERT INTO transaction (issued_at) VALUES (?)
    params: (datetime.utcnow())
3. INSERT INTO article_version (id, name, content, transaction_id) VALUES (?, ?, ?, ?)
    params: (<article id from query 1>, 'Some article', 'Some content', <transaction id from query 2>)
```

