import pytest
import sqlalchemy as sa
from sqlalchemy.orm import column_property, declared_attr

from sqlalchemy_history import version_class, versioning_manager
from tests import TestCase, create_test_cases


class SingleTableInheritanceTestCase(TestCase):
    def create_models(self, decl_base, versioning_options):
        class TextItem(decl_base):
            __tablename__ = "text_item"
            __versioned__ = {"base_classes": (decl_base,)}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )

            discriminator = sa.Column(sa.Unicode(100))

            __mapper_args__ = {
                "polymorphic_on": discriminator,
                "polymorphic_identity": "base",
                "with_polymorphic": "*",
            }

        class Article(TextItem):
            __mapper_args__ = {"polymorphic_identity": "article"}
            name = sa.Column(sa.Unicode(255))

            @declared_attr
            def status(cls):  # noqa: N805
                return sa.Column("_status", sa.Unicode(255))

        class BlogPost(TextItem):
            __mapper_args__ = {"polymorphic_identity": "blog_post"}
            title = sa.Column(sa.Unicode(255))

        self.TextItem = TextItem
        self.Article = Article
        self.BlogPost = BlogPost

    @pytest.fixture(autouse=True)
    def setup_method_for_single_inheritance_objects(self, session):
        self.TextItemVersion = version_class(self.TextItem)
        self.ArticleVersion = version_class(self.Article)
        self.BlogPostVersion = version_class(self.BlogPost)
        yield
        del self.TextItemVersion, self.ArticleVersion, self.BlogPostVersion

    def test_inheritance(self):
        assert issubclass(self.ArticleVersion, self.TextItemVersion)
        assert issubclass(self.BlogPostVersion, self.TextItemVersion)

    def test_version_class_map(self):
        manager = self.TextItem.__versioning_manager__
        assert len(manager.version_class_map.keys()) == 3

    def test_each_class_has_distinct_version_class(self):
        assert self.TextItemVersion.__table__.name == "text_item_version"
        assert self.ArticleVersion.__table__.name == "text_item_version"
        assert self.BlogPostVersion.__table__.name == "text_item_version"

    def test_each_object_has_distinct_version_class(self, session):
        article = self.Article()
        blogpost = self.BlogPost()
        textitem = self.TextItem()

        session.add(article)
        session.add(blogpost)
        session.add(textitem)
        session.commit()

        assert type(textitem.versions[0]) is self.TextItemVersion
        assert type(article.versions[0]) is self.ArticleVersion
        assert type(blogpost.versions[0]) is self.BlogPostVersion

    def test_transaction_changed_entities(self, session):
        article = self.Article()
        article.name = "Text 1"
        session.add(article)
        session.commit()
        Transaction = versioning_manager.transaction_cls
        transaction = session.scalars(
            sa.select(Transaction).order_by(sa.sql.expression.desc(Transaction.issued_at))
        ).first()
        assert transaction.entity_names == ["Article"]
        assert transaction.changed_entities

    def test_declared_attr_inheritance(self):
        assert self.ArticleVersion.status


create_test_cases(SingleTableInheritanceTestCase)


class TestCaseStatementPolymorphicOn(TestCase):
    def create_models(self, decl_base, versioning_options):
        class Writer(decl_base):
            __tablename__ = "writer"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))
            type = sa.Column(sa.Unicode(255))

            __mapper_args__ = {
                "polymorphic_on": sa.case(
                    (type.in_(["poet", "lyricist"]), "bard"),  # noqa: A003
                    else_=type,  # noqa: A003
                ),
                "polymorphic_identity": "writer",
            }

        class Bard(Writer):
            __mapper_args__ = {"polymorphic_identity": "bard"}

        self.Writer = Writer
        self.Bard = Bard

    def test_adapts_case_statement_to_version_table(self):
        writer_version = version_class(self.Writer)
        discriminator = sa.inspect(writer_version).polymorphic_on
        discriminator_columns = {
            element for element in sa.sql.visitors.iterate(discriminator) if isinstance(element, sa.Column)
        }

        assert discriminator_columns
        assert {column.table for column in discriminator_columns} == {writer_version.__table__}

    def test_loads_matching_version_subclass(self, session):
        writer = self.Bard(name="Some poet", type="poet")
        session.add(writer)
        session.commit()

        writer_version = version_class(self.Writer)
        bard_version = version_class(self.Bard)
        version = session.scalars(sa.select(writer_version)).one()

        assert isinstance(version, bard_version)
        assert version.type == "poet"


class TestColumnPropertyPolymorphicOn(TestCase):
    def create_models(self, decl_base, versioning_options):
        class Employee(decl_base):
            __tablename__ = "employee"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            discriminator = sa.Column(sa.String(50))
            employee_type = column_property(
                sa.case(
                    (discriminator == "EN", "engineer"),
                    (discriminator == "MA", "manager"),
                    else_="employee",
                )
            )

            __mapper_args__ = {
                "polymorphic_on": "employee_type",
                "polymorphic_identity": "employee",
            }

        class Engineer(Employee):
            __mapper_args__ = {"polymorphic_identity": "engineer"}

        class Manager(Employee):
            __mapper_args__ = {"polymorphic_identity": "manager"}

        self.Employee = Employee
        self.Engineer = Engineer
        self.Manager = Manager

    def test_adapts_column_property_expression_and_loads_version_subclasses(self, session):
        employees = [
            self.Engineer(discriminator="EN"),
            self.Manager(discriminator="MA"),
            self.Employee(discriminator="OTHER"),
        ]
        session.add_all(employees)
        session.commit()

        employee_version = version_class(self.Employee)
        discriminator = sa.inspect(employee_version).polymorphic_on
        discriminator_columns = {
            element for element in sa.sql.visitors.iterate(discriminator) if isinstance(element, sa.Column)
        }
        versions = session.scalars(sa.select(employee_version).order_by(employee_version.id)).all()

        assert {column.key for column in discriminator_columns} == {"discriminator"}
        assert {column.table for column in discriminator_columns} == {employee_version.__table__}
        assert [type(version) for version in versions] == [
            version_class(self.Engineer),
            version_class(self.Manager),
            employee_version,
        ]


class TestComplexCaseStatementPolymorphicOn(TestCase):
    def create_models(self, decl_base, versioning_options):
        class Writer(decl_base):
            __tablename__ = "complex_writer"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            category = sa.Column(sa.Unicode(255))
            kind = sa.Column(sa.Unicode(255))
            score = sa.Column(sa.Integer)
            active = sa.Column(sa.Boolean)

            __mapper_args__ = {
                "polymorphic_on": sa.case(
                    (
                        category == "creative",
                        sa.case(
                            (sa.and_(kind.in_(["poet", "lyricist"]), score >= 80), "bard"),
                            else_="writer",
                        ),
                    ),
                    (sa.and_(category == "technical", active == sa.true()), "technical_writer"),
                    else_="writer",
                ),
                "polymorphic_identity": "writer",
            }

        class Bard(Writer):
            __mapper_args__ = {"polymorphic_identity": "bard"}

        class TechnicalWriter(Writer):
            __mapper_args__ = {"polymorphic_identity": "technical_writer"}

        self.Writer = Writer
        self.Bard = Bard
        self.TechnicalWriter = TechnicalWriter

    def test_adapts_all_columns_in_nested_case_statement(self):
        writer_version = version_class(self.Writer)
        discriminator = sa.inspect(writer_version).polymorphic_on
        discriminator_columns = {
            element for element in sa.sql.visitors.iterate(discriminator) if isinstance(element, sa.Column)
        }

        assert {column.key for column in discriminator_columns} == {"category", "kind", "score", "active"}
        assert {column.table for column in discriminator_columns} == {writer_version.__table__}

    def test_loads_subclasses_from_nested_case_branches(self, session):
        writers = [
            self.Bard(category="creative", kind="poet", score=90, active=True),
            self.TechnicalWriter(category="technical", kind="manual", score=50, active=True),
            self.Writer(category="creative", kind="novelist", score=70, active=True),
        ]
        session.add_all(writers)
        session.commit()

        writer_version = version_class(self.Writer)
        versions = session.scalars(sa.select(writer_version).order_by(writer_version.id)).all()

        assert [type(version) for version in versions] == [
            version_class(self.Bard),
            version_class(self.TechnicalWriter),
            writer_version,
        ]
