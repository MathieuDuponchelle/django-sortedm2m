# -*- coding: utf-8 -*-
import sys
from itertools import chain
from django import forms
from django.conf import settings
from django.db.models.query import QuerySet
from django.template.loader import render_to_string
from django.utils.encoding import force_text
from django.utils.html import conditional_escape, escape
from django.utils.safestring import mark_safe
import photologue.models

if sys.version_info[0] < 3:
    iteritems = lambda d: iter(d.iteritems())
    string_types = basestring,
    str_ = unicode
else:
    iteritems = lambda d: iter(d.items())
    string_types = str,
    str_ = str


STATIC_URL = getattr(settings, 'STATIC_URL', settings.MEDIA_URL)

def admin_thumbnail(photo):
    func = getattr(photo, 'get_admin_thumbnail_url', None)
    if hasattr(photo, 'get_absolute_url'):
        return u'<a href="%s"><img src="%s"></a>' % \
                (photo.get_absolute_url(), func())
    else:
        return u'<a href="%s"><img src="%s"></a>' % \
                (photo.image.url, func())

admin_thumbnail.short_description = "Thumbnail"
admin_thumbnail.allow_tags = True

class SortedCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    class Media:
        js = (
            STATIC_URL + 'sortedm2m/widget.js',
            STATIC_URL + 'sortedm2m/jquery-ui.js',
        )
        css = {'screen': (
            STATIC_URL + 'sortedm2m/widget.css',
        )}

    def build_attrs(self, attrs=None, **kwargs):
        attrs = super(SortedCheckboxSelectMultiple, self).\
            build_attrs(attrs, **kwargs)
        classes = attrs.setdefault('class', '').split()
        classes.append('sortedm2m')
        attrs['class'] = ' '.join(classes)
        return attrs


    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)

        # Normalize to strings
        str_values = [force_text(v) for v in value]

        selected = []
        unselected = []

        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            photo = photologue.models.Photo.objects.get(title=option_label)
            thumb = photo.get_custom_admin_url()
            custom_height = photo.get_height_for_custom_admin_width()
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = ' for="%s"' % str(photo.id)
            else:
                label_for = ''

            cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_text(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_text(option_label))
            item = {'label_for': label_for, 'rendered_cb': rendered_cb,
                    'option_label': option_label, 'option_value': option_value,
                    'thumb': thumb, 'custom_height': custom_height}
            if option_value in str_values:
                selected.append(item)
            else:
                unselected.append(item)

        # re-order `selected` array according str_values which is a set of `option_value`s in the order they should be shown on screen
        ordered = []
        for value in str_values:
            for select in selected:
                if value == select['option_value']:
                    ordered.append(select)
        selected = ordered

        print len(selected)
        print len(unselected)
        html = render_to_string(
            'sortedm2m/sorted_checkbox_select_multiple_widget.html',
            {'selected': selected, 'unselected': unselected})
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        print "name is", name
        print "value is", value
        if isinstance(value, string_types):
            print [v for v in value.split(',') if v]
            return [v for v in value.split(',') if v]
        return value


class SortedMultipleChoiceField(forms.ModelMultipleChoiceField):
    widget = SortedCheckboxSelectMultiple

    def clean(self, value):
        queryset = super(SortedMultipleChoiceField, self).clean(value)
        if value is None or not isinstance(queryset, QuerySet):
            return queryset
        object_list = dict((
            (str_(key), value)
            for key, value in iteritems(queryset.in_bulk(value))))
        return [object_list[str_(pk)] for pk in value]
