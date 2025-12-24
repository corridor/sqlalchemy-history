from copy import copy
from tests import TestCase
import sqlalchemy as sa


class TestWriteOnlyOneToManyRelationships(TestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)

        class Tag(self.Model):
            __tablename__ = "tag"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
            article = sa.orm.relationship(Article, backref=sa.orm.backref("tags", lazy="write_only"))

        self.Article = Article
        self.Tag = Tag

    def test_reflects_write_only_relationships_as_write_only(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        self.session.add(article)
        self.session.commit()

        # Verify the relationship is write_only and has select() method
        version = article.versions[0]
        assert hasattr(version.tags, "select")

        # Verify select() returns a Select statement
        select_stmt = version.tags.select()
        assert isinstance(select_stmt, sa.sql.Select)

        # Execute the select to verify it's lazy and can be queried
        result = self.session.execute(select_stmt).scalars().all()
        assert isinstance(result, list)

    def test_write_only_relationship_with_tags(self):
        article = self.Article()
        article.name = "Article with tags"
        article.content = "Content here"
        self.session.add(article)

        tag1 = self.Tag(name="Python", article=article)
        tag2 = self.Tag(name="SQLAlchemy", article=article)
        self.session.add_all([tag1, tag2])
        self.session.commit()

        # Verify the version relationship is lazy
        version = article.versions[0]
        select_stmt = version.tags.select()
        tags = self.session.execute(select_stmt).scalars().all()

        # Tags should be retrievable via select()
        assert len(tags) == 2
        assert any(tag.name == "Python" for tag in tags)
        assert any(tag.name == "SQLAlchemy" for tag in tags)


class TestWriteOnlyManyToManyRelationships(TestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {"base_classes": (self.Model,)}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        article_tag = sa.Table(
            "article_tag",
            self.Model.metadata,
            sa.Column(
                "article_id",
                sa.Integer,
                sa.ForeignKey("article.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("tag_id", sa.Integer, sa.ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
        )

        class Tag(self.Model):
            __tablename__ = "tag"
            __versioned__ = {"base_classes": (self.Model,)}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        Tag.articles = sa.orm.relationship(
            Article, secondary=article_tag, backref=sa.orm.backref("tags", lazy="write_only")
        )

        self.Article = Article
        self.Tag = Tag

    def test_version_relations(self):
        article = self.Article()
        article.name = "Some article"
        self.session.add(article)
        self.session.commit()

        # Verify the relationship is write_only and has select() method
        version = article.versions[0]
        assert hasattr(version.tags, "select")

        # Verify select() returns a Select statement
        select_stmt = version.tags.select()
        assert isinstance(select_stmt, sa.sql.Select)

    def test_write_only_many_to_many_with_data(self):
        article = self.Article()
        article.name = "Article about Python"
        self.session.add(article)

        tag1 = self.Tag(name="Python")
        tag2 = self.Tag(name="Programming")
        self.session.add_all([tag1, tag2])
        self.session.flush()

        # Add tags to article using add() method
        article.tags.add(tag1)
        article.tags.add(tag2)
        self.session.commit()

        # Verify the version relationship is write_only
        version = article.versions[0]
        select_stmt = version.tags.select()
        tags = self.session.execute(select_stmt).scalars().all()

        # Tags should be retrievable via select()
        assert len(tags) == 2
        assert any(tag.name == "Python" for tag in tags)
        assert any(tag.name == "Programming" for tag in tags)
