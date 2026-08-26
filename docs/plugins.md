---
icon: lucide/plug
---

# Plugins

```python
>>> from sqlalchemy_history.plugins import PropertyModTrackerPlugin
>>> versioning_manager.plugins.append(PropertyModTrackerPlugin())
>>> versioning_manager.plugins
<PluginCollection [...]>
>>> del versioning_manager.plugins[0] # You can also remove plugin
```

## Custom plugins

Subclass `Plugin` to hook into the versioning workflow. For example,
`transaction_args()` supplies values when a transaction is created; see
[Associate transactions with a user](transactions.md#associate-transactions-with-a-user).

## Activity

::: sqlalchemy_history.plugins.activity

## PropertyModTracker

::: sqlalchemy_history.plugins.property_mod_tracker

## TransactionChanges

::: sqlalchemy_history.plugins.transaction_changes

## TransactionMeta

::: sqlalchemy_history.plugins.transaction_meta
