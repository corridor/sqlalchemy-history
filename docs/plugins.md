# Plugins

```python
>>> from sqlalchemy_history.plugins import PropertyModTrackerPlugin
>>> versioning_manager.plugins.append(PropertyModTrackerPlugin())
>>> versioning_manager.plugins
<PluginCollection [...]>
>>> del versioning_manager.plugins[0] # You can also remove plugin
```

## Activity

::: sqlalchemy_history.plugins.activity

## PropertyModTracker

::: sqlalchemy_history.plugins.property_mod_tracker

## TransactionChanges

::: sqlalchemy_history.plugins.transaction_changes

## TransactionMeta

::: sqlalchemy_history.plugins.transaction_meta
