from pytest import raises

from matcher.scheme import ExportTemplate, ExternalObject, ObjectLink, Platform
from matcher.scheme.enums import ExportRowType
from matcher.scheme.views import AttributesView


def test_export_template_need():
    template = ExportTemplate()

    template.fields = []
    assert template.needs == set(), "should have no need"

    template.fields = [{"value": "'foo'"}, {"value": "3 + 2"}]
    assert template.needs == set(), "should have no need"

    template.fields = [{"value": "foo"}, {"value": "bar + baz"}]
    assert template.needs == set(["foo", "bar", "baz"]), "should extract the needs"

    template.fields = [{"value": "foo"}, {"value": "bar + foo"}, {"value": "bar"}]
    assert template.needs == set(["foo", "bar"]), "should deduplicate the needs"


def test_export_template_links():
    template = ExportTemplate()

    template.fields = []
    assert template.links == [], "should have no link"

    template.fields = [{"value": "foo"}]
    assert template.links == [], "should have no link"

    template.fields = [{"value": "links['foo'] + bar"}]
    assert template.links == ["foo"], "should extract the link"

    template.fields = [{"value": "mainlinks + linksbar + mainlinks['bar']"}]
    assert template.links == [], "should not be fooled by value including `links`"

    template.fields = [{"value": "links['foo']"}, {"value": "links['bar'] + links['foo']"}]
    assert template.links == ["bar", "foo"], "should dedupe links"

    template.fields = [{"value": "links['bar'] + links['foo']"}]
    tmp_links = template.links
    template.fields = [{"value": "links['foo'] + links['bar']"}]
    assert template.links == tmp_links, "order should stay the same"


def test_export_template_header():
    template = ExportTemplate()

    template.fields = []
    assert template.header == "", "header should be empty"

    template.fields = [{"name": "foo"}, {"name": "bar"}]
    assert template.header == "foo\tbar", "header should be correctly generated"

    template.fields = [{}, {}, {}]
    assert template.header == "\t\t", "empty column headers should stay as such"

    template.fields = [{"name": "foo\tbar"}, {"name": '"baz"'}]
    assert template.header == "\"foo\\\tbar\"\t\"\\\"baz\\\"\"", "column should be quoted"


def test_export_template_to_context():
    platform = Platform()
    external_object = ExternalObject()
    object_link = ObjectLink(external_object=external_object,
                             platform=platform,
                             external_id='foo')

    context = ExportTemplate(
        row_type=ExportRowType.EXTERNAL_OBJECT,
        fields=[]
    ).to_context((external_object, ))
    assert context == {
        'external_object': external_object,
        'links': {}
    }

    # OBJECT_LINK rows should have the `current` link
    context = ExportTemplate(
        row_type=ExportRowType.OBJECT_LINK,
        fields=[]
    ).to_context((object_link, external_object, ))
    assert context == {
        'external_object': external_object,
        'links': {'current': 'foo'}
    }

    # OBJECT_LINK rows should be able to request the platform
    context = ExportTemplate(
        row_type=ExportRowType.OBJECT_LINK,
        fields=[{"value": "platform.name"}]
    ).to_context((object_link, external_object, ))

    assert context == {
        'external_object': external_object,
        'platform': platform,
        'links': {'current': 'foo'}
    }

    # EXTERNAL_OBJECT rows shall not ask for the platform
    with raises(Exception, message="Platform can't be queried when the row_type is EXTERNAL_OBJECT"):
        context = ExportTemplate(
            row_type=ExportRowType.PLATFORM,
            fields=[{"value": "platform.name"}]
        ).to_context((object_link, external_object, ))

    # Requested links should be there
    context = ExportTemplate(
        row_type=ExportRowType.EXTERNAL_OBJECT,
        fields=[{"value": "links['foo']"}]
    ).to_context((external_object, 'bar', ))
    assert context == {
        'external_object': external_object,
        'links': {'foo': 'bar'}
    }

    context = ExportTemplate(
        row_type=ExportRowType.EXTERNAL_OBJECT,
        fields=[{"value": "attributes.country | join(',')"}]
    ).to_context((external_object, ))
    assert 'attributes' in context
    assert context['attributes'].view != external_object.attributes, \
        "an empty AttributesView should be associated with the attributes"
    assert context['attributes'].titles == [], "attributes should fall back to empty lists"

    with raises(AttributeError):
        # Invalid attributes should fail
        context['attributes'].foo

    # Let's set some attributes
    external_object.attributes = AttributesView(titles=['foo'])
    context = ExportTemplate(
        row_type=ExportRowType.EXTERNAL_OBJECT,
        fields=[{"value": "attributes.titles[0]"}]
    ).to_context((external_object, ))
    assert 'attributes' in context
    assert context['attributes'].view == external_object.attributes, "the AttributesView should be associated"
    assert context['attributes'].titles == ["foo"], "attributes that are set should work"
    assert context['attributes'].genres == [], "attributes that are not set should fall back to empty arrays"

    with raises(AttributeError):
        # Invalid attributes should fail
        context['attributes'].foo

    # Let's set some attributes
    context = ExportTemplate(
        row_type=ExportRowType.EXTERNAL_OBJECT,
        fields=[{"value": "zones.EUROBS"}]
    ).to_context((external_object, ))
    assert 'zones' in context, "the context should include zone informations"
    assert 'FR' in context['zones'].EUROBS, "the zones should have some data in them"


def test_exporte_template_compile_template():
    assert ExportTemplate(fields=[]).template == ""
    assert ExportTemplate(fields=[{"value": "foo"}, {"value": "bar"}]).template \
        == "{{ (foo) | quote }}\t{{ (bar) | quote }}"

    template = ExportTemplate(fields=[{"value": "foo"}, {"value": "bar"}]).compile_template()
    assert template({'foo': 'hello', 'bar': 'world'}) == 'hello\tworld', "the compiled template should be a callable"
