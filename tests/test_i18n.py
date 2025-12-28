import pytest

import sqlalchemy as sa
from sqlalchemy_history import versioning_manager
from sqlalchemy_i18n import Translatable, make_translatable, translation_base
from sqlalchemy_utils import i18n
from tests.__init__ import TestCase


i18n.get_locale = lambda: "en"
make_translatable()


@pytest.mark.skipif(str(sa.__version__).startswith("2."), reason="i18n doesn't support sqla 2.0 yet")
class TestVersioningWithI18nExtension(TestCase):
    def create_models(self):
        class Versioned(self.Model):
            __abstract__ = True
            __versioned__ = {"base_classes": (self.Model,)}

        class Article(self.Model, Translatable):
            __tablename__ = "article"
            __versioned__ = {"base_classes": (self.Model,)}
            __translatable__ = {"locales": ["fi", "en"]}
            locale = "en"

            kwargs = dict(primary_key=True)
            if self.driver != "sqlite":
                kwargs["autoincrement"] = True
            # FIXME: Currently SQLA_I18n package internally makes column attribute `autoincrement=False`
            #        Due to which Indenity gets a conflict as Identity should always have `autoincrment=True`
            # refer: https://github.com/kvesteri/sqlalchemy-i18n/blob/master/sqlalchemy_i18n/manager.py#L55
            #      : https://docs.sqlalchemy.org/en/14/core/defaults.html#identity-ddl
            id = sa.Column(sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), **kwargs)
            description = sa.Column(sa.UnicodeText)

        class ArticleTranslation(translation_base(Article)):
            __tablename__ = "article_translation"
            __versioned__ = {"base_classes": (self.Model,)}
            name = sa.Column("name", sa.Unicode(255))
            content = sa.Column("content", sa.UnicodeText)

        self.Article = Article

    def test_changeset(self):
        article = self.Article()
        article.name = "Some article"
        self.session.add(article)
        self.session.commit()

        assert article.translations["en"].versions[0].changeset

    def test_changed_entities(self):
        article = self.Article()
        article.description = "something"
        self.session.add(article)
        self.session.commit()
        article.name = "Some article"
        self.session.commit()

        tx_log = versioning_manager.transaction_cls
        tx = self.session.scalars(sa.select(tx_log).order_by(sa.desc(tx_log.id))).first()
        assert "ArticleTranslation" in tx.entity_names

    def test_history_with_many_translations(self):
        self.article = self.Article()
        self.article.description = "Some text"
        self.session.add(self.article)

        self.article.translations.fi.name = "Text 1"
        self.article.translations.en.name = "Text 2"

        self.session.commit()

        Transaction = versioning_manager.transaction_cls
        transaction = self.session.scalars(sa.select(Transaction)).one()

        assert len(transaction.changes) == 2
        assert "ArticleTranslation" in {chng.entity_name for chng in transaction.changes}
