from sqlalchemy.orm.session import Session

from sqlalchemy_history import UnitOfWork, versioning_manager
from tests import TestCase


class TestSessions(TestCase):
    plugins = []

    def test_multiple_connections(self, session, engine):
        with engine.connect() as conn2, Session(bind=conn2) as session2:
            article = self.Article(name="Session1 article")
            article2 = self.Article(name="Session2 article")
            session.add(article)
            session2.add(article2)
            session.flush()
            session2.flush()

            session.commit()
            session2.commit()
            assert article.versions.all()[-1].transaction_id
            assert article2.versions.all()[-1].transaction_id > article.versions.all()[-1].transaction_id

    def test_connection_binded_to_engine(self, setup_tables, engine):
        with Session(bind=engine) as session2:
            article = self.Article(name="Session1 article")
            session2.add(article)
            session2.commit()
            assert article.versions.all()[-1].transaction_id

    def test_manual_transaction_creation(self, session):
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        session.flush()
        assert transaction.id
        article = self.Article(name="Session1 article")
        session.add(article)
        session.flush()
        assert uow.current_transaction.id

        session.commit()
        assert article.versions.all()[-1].transaction_id

    def test_commit_without_objects(self, session):
        session.commit()


class TestUnitOfWork(TestCase):
    def test_with_session_arg(self, session):
        uow = versioning_manager.unit_of_work(session)
        assert isinstance(uow, UnitOfWork)


class TestExternalTransactionSession(TestCase):
    def test_session_with_external_transaction(self, setup_tables, engine):
        with engine.connect() as conn:
            t = conn.begin()
            with Session(bind=conn) as session:
                article = self.Article(name="My Session Article")
                session.add(article)
                session.flush()

            t.rollback()
