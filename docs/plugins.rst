Plugins
=======

Using plugins
-------------


::

    from sqlalchemy_continuum.plugins import PropertyModTrackerPlugin


    versioning_manager.plugins.append(PropertyModTrackerPlugin())


    versioning_manager.plugins  # <PluginCollection [...]>

    # You can also remove plugin

    del versioning_manager.plugins[0]


Activity
--------

.. automodule:: sqlalchemy_continuum.plugins.activity


.. _property-mod-tracker:

PropertyModTracker
------------------

.. automodule:: sqlalchemy_continuum.plugins.property_mod_tracker


TransactionChanges
------------------

.. automodule:: sqlalchemy_continuum.plugins.transaction_changes


TransactionMeta
---------------

.. automodule:: sqlalchemy_continuum.plugins.transaction_meta
