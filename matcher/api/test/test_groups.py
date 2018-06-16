from flask_sqlalchemy import SQLAlchemy
from injector import inject
from matcher.scheme.platform import Platform, PlatformGroup, PlatformType
from matcher.test import TestCase


class GroupTest(TestCase):
    @inject
    def test_list(self, db: SQLAlchemy):
        response = self.client.get("/api2/groups/")
        self.assertEqual(response.json["items"], [])

        group = PlatformGroup(name='foo')
        db.session.add(group)
        db.session.commit()
        response = self.client.get("/api2/groups/")
        self.assertEqual(response.json["items"], [{
            'id': group.id,
            'name': group.name,
            'platforms': []
        }])

    @inject
    def test_create(self, db: SQLAlchemy):
        response = self.client.post("/api2/groups/", data={'name': 'foo'})

        assert 'id' in response.json
        assert 'name' in response.json
        assert response.json['name'] == 'foo'

        group = db.session.query(PlatformGroup).get(response.json['id'])
        assert group is not None
        assert group.id == response.json['id']
        assert group.name == response.json['name']

    @inject
    def test_get(self, db: SQLAlchemy):
        group = PlatformGroup(name='foo')
        db.session.add(group)
        db.session.commit()

        response = self.client.get("/api2/groups/{}".format(group.id))
        self.assertEqual(response.json, {
            'id': group.id,
            'name': group.name,
            'platforms': []
        })

        platform = Platform(name='bar', slug='bar', type=PlatformType.INFO, country='US', group=group)
        db.session.add(group)
        db.session.commit()

        response = self.client.get("/api2/groups/{}".format(group.id))
        self.assertEqual(response.json, {
            'id': group.id,
            'name': group.name,
            'platforms': [{
                'id': platform.id,
                'type': 'info',
                'slug': platform.slug,
                'name': platform.name,
                'country': platform.country,
            }]
        })

        db.session.delete(group)
        db.session.commit()

        response = self.client.get("/api2/groups/{}".format(group.id))
        self.assert404(response)

    @inject
    def test_delete(self, db: SQLAlchemy):
        group = PlatformGroup(name='foo')
        db.session.add(group)
        db.session.commit()

        group_id = group.id
        db.session.expire(group)

        response = self.client.delete("/api2/groups/{}".format(group_id))
        assert response.json == 'ok'

        assert db.session.query(PlatformGroup).get(group_id) is None

    @inject
    def test_put(self, db: SQLAlchemy):
        group = PlatformGroup(name='foo')
        db.session.add(group)
        db.session.commit()

        response = self.client.put("/api2/groups/{}".format(group.id), data={'name': 'bar'})
        assert response.json['name'] == 'bar'

        db.session.refresh(group)
        assert group.name == 'bar'
