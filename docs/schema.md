# Schema

## Version tables

By default SQLAlchemy-History creates a version table for each
versioned entity table. The version tables are suffixed with
'version'. So for example if you have two versioned tables 'article'
and 'category', SQLAlchemy-History would create two version tables
'articleversion' and 'categoryversion'.

By default the version tables contain these columns:

  - id of the original entity (this can be more then one column in the
    case of composite primary keys)
  - transactionid - an integer that matches to the id number in the
    transactionlog table.
  - endtransactionid - an integer that matches the next version
    record's transactionid. If this is the current version record then
    this field is null.
  - operationtype - a small integer defining the type of the operation
  - versioned fields from the original entity

If you are using `property-mod-tracker` SQLA-History also creates one
boolean field for each versioned field. By default these boolean fields
are suffixed with 'mod'.

The primary key of each version table is the combination of parent
table's primary key + the transactionid. This means there can be at
most one version table entry for a given entity instance at given
transaction.

## Transaction tables

By default SQLA-History creates one transaction table called
**transaction. Many SQLA-History plugins also
create additional tables for efficient transaction storage. If you wish
to query efficiently transactions afterwards you should consider using
some of these plugins.

The transaction table only contains two fields by default: id and
issuedat.
