from __future__ import annotations

import datetime

import sqlalchemy as sa

from sqlalchemy_history import version_class
from sqlalchemy_history.operation import Operation
from sqlalchemy_history.schema import update_end_tx_column
from sqlalchemy_history.utils import version_table
from tests import TestCase, create_test_cases


class UpdateEndTransactionID(TestCase):
    versioning_strategy = "validity"

    def create_models(self):
        super().create_models()
        article_label_table = sa.Table(
            "article_label",
            self.Model.metadata,
            sa.Column(
                "article_id",
                sa.Integer,
                sa.ForeignKey("article.id"),
                primary_key=True,
                nullable=False,
            ),
            sa.Column("label_id", sa.Integer, sa.ForeignKey("label.id"), primary_key=True, nullable=False),
            sa.Column(
                "created_date",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.current_timestamp(),
                default=lambda: datetime.datetime.now(datetime.timezone.utc),
            ),
        )

        class Label(self.Model):
            __tablename__ = "label"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(self.Article.id))
            article = sa.orm.relationship(self.Article, backref="labels", secondary=article_label_table)

        self.article_label_table = article_label_table
        self.Label = Label

    def _insert(self, values):
        table = version_class(self.Article).__table__
        stmt = table.insert().values(values)
        self.session.execute(stmt)

    def test_update_end_transaction_id(self):
        table = version_class(self.Article).__table__
        self._insert(
            {
                "id": 1,
                "transaction_id": 1,
                "name": "Article 1",
                "operation_type": 1,
            },
        )
        self._insert(
            {
                "id": 1,
                "transaction_id": 2,
                "name": "Article 1 updated",
                "operation_type": 2,
            },
        )
        self._insert(
            {
                "id": 2,
                "transaction_id": 3,
                "name": "Article 2",
                "operation_type": 1,
            },
        )
        self._insert(
            {
                "id": 1,
                "transaction_id": 4,
                "name": "Article 1 updated (again)",
                "operation_type": 2,
            },
        )
        self._insert(
            {
                "id": 2,
                "transaction_id": 5,
                "name": "Article 2 updated",
                "operation_type": 2,
            },
        )
        if self.versioning_strategy == "validity":
            update_end_tx_column(table, conn=self.session)
            rows = self.session.execute(
                sa.text("SELECT * FROM article_version ORDER BY transaction_id"),
            ).fetchall()
            assert rows[0].transaction_id == 1
            assert rows[0].end_transaction_id == 2
            assert rows[1].transaction_id == 2
            assert rows[1].end_transaction_id == 4
            assert rows[2].transaction_id == 3
            assert rows[2].end_transaction_id == 5
            assert rows[3].transaction_id == 4
            assert rows[3].end_transaction_id is None
            assert rows[4].transaction_id == 5
            assert rows[4].end_transaction_id is None
        elif self.versioning_strategy == "subquery":
            rows = self.session.execute(
                sa.text("SELECT * FROM article_version ORDER BY transaction_id"),
            ).fetchall()
            assert not hasattr(rows[0], "end_transaction_id")

    def test_assoc_update_end_transaction_id(self):
        article_label_table_version = version_table(self.article_label_table)

        label = self.Label(name="first label")
        label2 = self.Label(name="second label")
        article = self.Article(name="Some article", content="Some content", labels=[label])
        self.session.add(article)
        self.session.commit()
        article.labels = [label2]
        self.session.commit()
        article.labels = [label, label2]
        self.session.commit()

        article.labels = [label]
        self.session.commit()
        rows = (
            self.session.query(article_label_table_version)
            .order_by(article_label_table_version.c.transaction_id)
            .all()
        )
        if self.versioning_strategy == "validity":
            assert rows[0].label_id == label.id
            assert rows[0].transaction_id == 1
            assert rows[0].end_transaction_id == 2
            assert rows[0].operation_type == Operation.INSERT

            assert rows[1].label_id == label.id
            assert rows[1].transaction_id == 2
            assert rows[1].end_transaction_id == 3
            assert rows[1].operation_type == Operation.DELETE

            assert {rows[2].label_id, rows[3].label_id} == {label.id, label2.id}
            assert rows[2].transaction_id == 2
            assert rows[2].end_transaction_id == 4
            assert rows[2].operation_type == Operation.INSERT
            assert rows[3].transaction_id == 3
            assert rows[3].end_transaction_id is None
            assert rows[3].operation_type == Operation.INSERT

            assert rows[4].label_id == label2.id
            assert rows[4].transaction_id == 4
            assert rows[4].end_transaction_id is None
            assert rows[4].operation_type == Operation.DELETE
        elif self.versioning_strategy == "subquery":
            assert not hasattr(rows[0], "end_transaction_id")


setting_variants = {
    "versioning_strategy": [
        "subquery",
        "validity",
    ],
}

create_test_cases(UpdateEndTransactionID, setting_variants)
