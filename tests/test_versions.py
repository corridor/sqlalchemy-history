from tests import TestCase
from sqlalchemy_history import versioning_manager


class TestVersions(TestCase):
    def test_versions_ordered_by_transaction(self):
        names = [
            "Some article",
            "Update 1 article",
            "Update 2 article",
            "Update 3 article",
        ]

        article = self.Article(name=names[0])
        self.session.add(article)
        self.session.commit()
        article.name = names[1]
        self.session.commit()
        article.name = names[2]
        self.session.commit()
        article.name = names[3]
        self.session.commit()

        for index, name in enumerate(names):
            assert article.versions[index].name == name

    def test_versions_with_unordered_transaction_id(self):
        # In some DBs - the sequence of IDs used for primary keys is not monotonic
        # This example is taken from: test_versions_ordered_by_transaction

        def create_transaction(id):
            # Use this fucntion to explicitly create transaction records where the ID
            # is not in increasing order
            transaction = versioning_manager.unit_of_work(self.session).create_transaction(self.session)
            transaction.id = id

        names = [
            "Some article",
            "Update 1 article",
            "Update 2 article",
            "Update 3 article",
        ]

        article = self.Article(name=names[0])
        self.session.add(article)
        create_transaction(id=4)
        self.session.commit()
        article.name = names[1]
        create_transaction(id=1)
        self.session.commit()
        article.name = names[2]
        create_transaction(id=3)
        self.session.commit()
        article.name = names[3]
        create_transaction(id=2)
        self.session.commit()

        for index, name in enumerate(names):
            assert article.versions[index].name == name
