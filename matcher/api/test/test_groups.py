from matcher.scheme.platform import Platform, PlatformGroup, PlatformType


def test_list(client, session):
    response = client.get("/api2/groups/")
    assert response.json["items"] == []

    group = PlatformGroup(name='foo')
    session.add(group)
    session.commit()
    response = client.get("/api2/groups/")
    assert response.json["items"] == [{
        'id': group.id,
        'name': group.name,
        'platforms': []
    }]


def test_create(client, session):
    response = client.post("/api2/groups/", data={'name': 'foo'})

    assert 'id' in response.json
    assert 'name' in response.json
    assert response.json['name'] == 'foo'

    group = session.query(PlatformGroup).get(response.json['id'])
    assert group is not None
    assert group.id == response.json['id']
    assert group.name == response.json['name']


def test_get(client, session):
    group = PlatformGroup(name='foo')
    session.add(group)
    session.commit()

    response = client.get("/api2/groups/{}".format(group.id))
    assert response.json == {
        'id': group.id,
        'name': group.name,
        'platforms': []
    }

    platform = Platform(name='bar', slug='bar', type=PlatformType.INFO, country='US', group=group)
    session.add(group)
    session.commit()

    response = client.get("/api2/groups/{}".format(group.id))
    assert response.json == {
        'id': group.id,
        'name': group.name,
        'platforms': [{
            'id': platform.id,
            'type': 'info',
            'slug': platform.slug,
            'name': platform.name,
            'country': platform.country,
        }]
    }

    session.delete(group)
    session.commit()

    response = client.get("/api2/groups/{}".format(group.id))
    assert response.status_code == 404


def test_delete(client, session):
    group = PlatformGroup(name='foo')
    session.add(group)
    session.commit()

    group_id = group.id
    session.expire(group)

    response = client.delete("/api2/groups/{}".format(group_id))
    assert response.json == 'ok'

    assert session.query(PlatformGroup).get(group_id) is None


def test_put(client, session):
    group = PlatformGroup(name='foo')
    session.add(group)
    session.commit()

    response = client.put("/api2/groups/{}".format(group.id), data={'name': 'bar'})
    assert response.json['name'] == 'bar'

    session.refresh(group)
    assert group.name == 'bar'
