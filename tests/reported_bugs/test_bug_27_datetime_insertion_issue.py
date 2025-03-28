import datetime
import sqlalchemy as sa
from copy import copy

from tests import TestCase


class TestBug27(TestCase):
    # ref: https://github.com/corridor/sqlalchemy-history/issues/27
    def create_models(self):
        article_author_table = sa.Table(
            "article_author",
            self.Model.metadata,
            sa.Column(
                "article_id", sa.Integer, sa.ForeignKey("article.id"), primary_key=True, nullable=False
            ),
            sa.Column("author_id", sa.Integer, sa.ForeignKey("author.id"), primary_key=True, nullable=False),
            sa.Column(
                "created_date",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.current_timestamp(),
                default=lambda: datetime.datetime.now(datetime.timezone.utc),
            ),
        )

        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)

        class Author(self.Model):
            __tablename__ = "author"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
            articles = sa.orm.relationship(Article, secondary=article_author_table, backref="authors")

        self.Article = Article
        self.Author = Author
        self.article_author_table = article_author_table

    def test_inserting_entries(self):
        article = self.Article(name="Article 1")
        author = self.Author(name="Author 1", articles=[article])
        self.session.add(article)
        self.session.add(author)
        self.session.commit()

        obj = self.session.query(self.article_author_table).all()
        assert len(obj) == 1
        assert isinstance(obj[0][-1], datetime.datetime)  # last col is a datetime!
