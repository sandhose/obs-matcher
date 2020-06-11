from wtforms import SelectFieldBase, widgets


class SelectAJAXMultipleField(SelectFieldBase):
    widget = widgets.Select(multiple=True)

    def __init__(
        self,
        label=None,
        validators=None,
        text_map=lambda li: ((v, v) for v in li),
        **kwargs,
    ):
        super(SelectAJAXMultipleField, self).__init__(label, validators, **kwargs)
        self.text_map = text_map

    def iter_choices(self):
        for (value, label) in self.text_map(self.data):
            yield (value, label, True)

    def process_data(self, value):
        try:
            self.data = list(value)
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        try:
            self.data = list(valuelist)
        except ValueError:
            raise ValueError(
                self.gettext(
                    "Invalid choice(s): one or more data inputs could not be coerced"
                )
            )
