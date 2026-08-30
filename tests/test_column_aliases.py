import sqlalchemy as sa

from sqlalchemy_history import version_class
from tests import TestCase, create_test_cases


class ColumnAliasesBaseTestCase(TestCase):
    def create_models(self):
        class TextItem(self.Model):
            __tablename__ = "text_item"
            __versioned__ = {}

            id = sa.Column(
                "_id",
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )

            name = sa.Column("_name", sa.Unicode(255))

        self.TextItem = TextItem


class TestVersionTableWithColumnAliases(ColumnAliasesBaseTestCase):
    def test_column_reflection(self):
        assert "_id" in [c.name for c in version_class(self.TextItem).__table__.c]


class ColumnAliasesTestCase(ColumnAliasesBaseTestCase):
    def test_insert(self, session):
        item = self.TextItem(name="Something")
        session.add(item)
        session.commit()
        assert item.versions[0].name == "Something"

    def test_revert(self, session):
        item = self.TextItem(name="Something")
        session.add(item)
        session.commit()
        item.name = "Some other thing"
        session.commit()
        item.versions[0].revert()
        session.commit()

    def test_previous_for_deleted_parent(self, session):
        item = self.TextItem()
        item.name = "Some item"
        item.content = "Some content"
        session.add(item)
        session.commit()
        session.delete(item)
        session.commit()
        TextItemVersion = version_class(self.TextItem)

        versions = session.scalars(
            sa.select(TextItemVersion).order_by(getattr(TextItemVersion, self.options["transaction_column_name"]))
        ).all()
        assert versions[1].previous.name == "Some item"


create_test_cases(ColumnAliasesTestCase)
