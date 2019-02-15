from wtforms import Form, StringField


class ProviderListFilter(Form):
    search = StringField("Search")
