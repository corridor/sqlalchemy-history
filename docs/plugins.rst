Plugins
=======

Using plugins
-------------


::

    from sqlalchemy_history.plugins import PropertyModTrackerPlugin


    versioning_manager.plugins.append(PropertyModTrackerPlugin())


    versioning_manager.plugins  # <PluginCollection [...]>

    # You can also remove plugin

    del versioning_manager.plugins[0]


Activity
--------

.. automodule:: sqlalchemy_history.plugins.activity


Flask
-----

.. automodule:: sqlalchemy_history.plugins.flask


.. _property-mod-tracker:

PropertyModTracker
------------------

.. automodule:: sqlalchemy_history.plugins.property_mod_tracker


TransactionChanges
------------------

.. automodule:: sqlalchemy_history.plugins.transaction_changes


TransactionMeta
---------------

.. automodule:: sqlalchemy_history.plugins.transaction_meta
