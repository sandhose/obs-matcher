from matcher.scheme.enums import PlatformType
from matcher.scheme.platform import Platform, PlatformGroup


def test_list(client, session):
    response = client.get("/api/platforms/")
    assert response.json["items"] == []

    platform = Platform(name="foo", slug="bar", type=PlatformType.INFO, country="US")
    session.add(platform)
    session.commit()
    response = client.get("/api/platforms/")
    assert response.json["items"] == [
        {
            "id": platform.id,
            "type": "info",
            "slug": platform.slug,
            "name": platform.name,
            "country": platform.country,
            "group": None,
        }
    ]


def test_create(client, session):
    response = client.post(
        "/api/platforms/",
        data={"type": "info", "slug": "bar", "name": "foo", "country": "US"},
    )

    assert "id" in response.json

    platform = session.query(Platform).get(response.json["id"])
    assert platform is not None
    assert platform.id == response.json["id"]
    assert platform.type == PlatformType.INFO
    assert platform.slug == "bar"
    assert platform.name == "foo"
    assert platform.country == "US"
    assert platform.group is None

    # slug should be unique
    response = client.post(
        "/api/platforms/",
        data={"type": "info", "slug": "bar", "name": "baz", "country": "US"},
    )

    assert response.status_code == 400
    assert response.json["type"] == "integrity_error"

    # invalid type
    response = client.post(
        "/api/platforms/",
        data={"type": "foo", "slug": "bar2", "name": "foo2", "country": "US"},
    )

    assert response.status_code == 400


def test_get(client, session):
    platform = Platform(name="foo", slug="bar", type=PlatformType.INFO, country="US")
    session.add(platform)
    session.commit()

    response = client.get("/api/platforms/{}".format(platform.id))
    assert response.json == {
        "id": platform.id,
        "type": "info",
        "slug": platform.slug,
        "name": platform.name,
        "country": platform.country,
        "group": None,
    }

    group = PlatformGroup(name="baz", platforms=[platform])
    session.add(group)
    session.commit()

    response = client.get("/api/platforms/{}".format(platform.id))
    assert response.json["group"] == {"id": group.id, "name": group.name}


def test_delete(client, session):
    platform = Platform(name="foo", slug="bar", type=PlatformType.INFO, country="US")
    session.add(platform)
    session.commit()

    platform_id = platform.id
    session.expire(platform)

    response = client.delete("/api/platforms/{}".format(platform.id))
    assert response.json == "ok"

    assert session.query(PlatformGroup).get(platform_id) is None


def test_put(client, session):
    platform = Platform(name="foo", slug="bar", type=PlatformType.INFO, country="US")
    session.add(platform)
    session.commit()

    response = client.put("/api/platforms/{}".format(platform.id), data={"name": "baz"})
    assert response.json["name"] == "baz"

    session.refresh(platform)
    assert platform.name == "baz"
