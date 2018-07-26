import json
from datetime import datetime
from http import HTTPStatus

import pytest

from matcher.scheme.enums import PlatformType, ScrapStatus
from matcher.scheme.platform import Platform, Scrap


@pytest.fixture(scope="function")
def platform(session):
    platform = Platform(name='foo', slug='fixture-platform', type=PlatformType.INFO)
    session.add(platform)
    yield platform
    session.delete(platform)


def test_list(client, session, platform):
    response = client.get("/api/scraps/")
    assert response.json["items"] == []

    scrap = Scrap(status=ScrapStatus.SCHEDULED, platform=platform, date=datetime.now())
    session.add(scrap)
    session.commit()
    response = client.get("/api/scraps/")
    assert response.json["items"] == [{
        'id': scrap.id,
        'status': str(scrap.status),
        'date': scrap.date.isoformat(),
        'platform': {
            'id': platform.id,
            'name': platform.name,
            'slug': platform.slug,
        }
    }]


def test_create(client, session, platform):
    response = client.post("/api/scraps/", data={'platform': platform.slug})

    assert response.status_code == HTTPStatus.OK
    assert 'id' in response.json
    assert 'status' in response.json
    assert 'date' in response.json
    assert 'platform' in response.json

    scrap = session.query(Scrap).get(response.json['id'])

    assert response.json['id'] == scrap.id
    assert response.json['status'] == 'scheduled'
    assert response.json['date'] == scrap.date
    assert response.json['platform'] == {'id': platform.id,
                                         'name': platform.name,
                                         'slug': platform.slug}

    # Setting the platform by id should work
    response = client.post("/api/scraps/", data={'platform': platform.id})
    assert response.status_code == HTTPStatus.OK
    assert response.json['platform']['slug'] == platform.slug

    # Directly transitionning to 'RUNNING' should work and set the date
    response = client.post("/api/scraps/", data={'platform': platform.id,
                                                 'status': 'running'})
    assert response.status_code == HTTPStatus.OK
    assert response.json['status'] == 'running'
    scrap = session.query(Scrap).get(response.json['id'])
    assert scrap.status == ScrapStatus.RUNNING
    assert scrap.date is not None
    assert response.json['date'] == scrap.date.isoformat()

    # Transitionning to other status should not work
    for status in ['aborted', 'success', 'failed']:
        response = client.post("/api/scraps/", data={'platform': platform.id,
                                                     'status': status})
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['type'] == 'invalid_transition'

    # Invalid parameter
    response = client.post("/api/scraps/")
    assert response.status_code == HTTPStatus.BAD_REQUEST

    # Platform not found
    response = client.post("/api/scraps/", data={'platform': 'non-existant'})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get(client, session, platform):
    scrap = Scrap(platform=platform)
    session.add(scrap)
    session.commit()

    response = client.get("/api/scraps/{}".format(scrap.id))
    assert response.json == {
        'id': scrap.id,
        'date': scrap.date,
        'status': 'scheduled',
        'platform': {
            'id': platform.id,
            'name': platform.name,
            'slug': platform.slug
        }
    }


def test_delete(client, session, platform):
    scrap = Scrap(platform=platform)
    session.add(scrap)
    session.commit()

    response = client.delete("/api/scraps/{}".format(scrap.id))
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_put(client, session, platform):
    scrap = Scrap(platform=platform)
    session.add(scrap)
    session.commit()

    response = client.put("/api/scraps/{}".format(scrap.id),
                          data=json.dumps({'status': 'running', 'stats': {'foo': 'bar'}}),
                          content_type='application/json',
                          headers={'X-Fields': 'date,status,stats'})
    assert response.json['status'] == 'running'

    session.refresh(scrap)
    assert scrap.date is not None
    assert scrap.date.isoformat() == response.json['date']
    assert scrap.status == ScrapStatus.RUNNING
    assert scrap.stats == {'foo': 'bar'}
    assert scrap.stats == response.json['stats']


transitions = [
    # Those are valid transitions
    ('scheduled', 'running', True),
    ('running', 'success', True),
    ('running', 'failed', True),
    ('running', 'aborted', True),
    ('failed', 'scheduled', True),
    ('aborted', 'scheduled', True),
    # Those are invalid transitions
    ('scheduled', 'aborted', False),
    ('scheduled', 'success', False),
    ('scheduled', 'failed', False),
    ('running', 'scheduled', False),
    ('aborted', 'running', False),
    ('aborted', 'success', False),
    ('aborted', 'failed', False),
    ('success', 'scheduled', False),
    ('success', 'running', False),
    ('success', 'aborted', False),
    ('success', 'failed', False),
    ('failed', 'running', False),
    ('failed', 'aborted', False),
    ('failed', 'success', False),
]


@pytest.mark.parametrize('from_status,to_status,valid', transitions)
def test_put_transitions(from_status, to_status, valid, client, session, platform):
    scrap = Scrap(platform=platform, status=ScrapStatus.from_name(from_status))
    session.add(scrap)
    session.commit()

    response = client.put("/api/scraps/{}".format(scrap.id), data={'status': to_status})

    if valid:
        assert response.status_code == HTTPStatus.OK
        assert response.json['status'] == to_status
        session.refresh(scrap)
        assert scrap.status == ScrapStatus.from_name(to_status)
    else:
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['type'] == 'invalid_transition'
