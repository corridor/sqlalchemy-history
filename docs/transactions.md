---
icon: lucide/arrow-left-right
---

# Transactions

## Transaction

For each committed transaction SQLAlchemy-History creates a new Transaction record.

Transaction can be queried just like any other sqlalchemy declarative model.

```python
>>> from sqlalchemy_history import transaction_class
>>> Transaction = transaction_class(Article)
>>> session.scalars(sa.select(Transaction)).all() # find all transactions
```

## Associate transactions with a user

Set `user_cls` to add `user` and `user_id` to the transaction model. A custom
[plugin](plugins.md) can populate the ID through `transaction_args` when each
transaction is created:

```python
from sqlalchemy.orm import Session

from sqlalchemy_history import UnitOfWork, make_versioned
from sqlalchemy_history.plugins import Plugin


class CurrentUserPlugin(Plugin):
    def transaction_args(self, uow: UnitOfWork, session: Session):
        user_id = session.info.get("current_user_id")
        return {"user_id": user_id} if user_id is not None else {}


make_versioned(user_cls="User", plugins=[CurrentUserPlugin()])
```

This example uses `session.info` to pass the ID, but this is not required. Ideally,
the plugin should get the current user ID from the authentication or user-session
mechanism used by your application.

If you use `session.info`, store the current user's ID before committing changes.
Remove it afterward so it is not accidentally used for a later transaction:

```python
session.info["current_user_id"] = user.id
try:
    session.commit()
finally:
    session.info.pop("current_user_id", None)
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
