import sqlalchemy as sa


@sa.event.listens_for(sa.orm.mapper, 'instrument_class')
def my_listener(mapper, cls):
    pass


sa.event.remove(
    sa.orm.mapper, 'instrument_class', my_listener
)
