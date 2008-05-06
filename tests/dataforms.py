#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import libxml2
from pyxmpp.jabber.dataforms import Form, Field, Option
from pyxmpp.jid import JID


class TestForm(unittest.TestCase):
    def test_empty_form_type(self):
        form = self.parse_form(empty_form)
        self.failUnlessEqual(form.type,"form")
        self.failIf(form.title)
        self.failIf(form.instructions)
        self.failIf(form.fields)
        self.failIf(form.items)
        self.failIf(form.reported_fields)
        self.failIf(list(form))
        form = self.parse_form(empty_submit)
        self.failUnlessEqual(form.type,"submit")
        form = self.parse_form(empty_cancel)
        self.failUnlessEqual(form.type,"cancel")
        form = self.parse_form(empty_result)
        self.failUnlessEqual(form.type,"result")

    def test_jep4_example2_basic(self):
        form = self.parse_form(jep4_example2)
        self.check_form_info(form, jep4_example2_info)

    def test_jep4_example2_iter(self):
        form = self.parse_form(jep4_example2)
        self.check_form_iter(form, jep4_example2_fields)

    def test_jep4_example2_mapping(self):
        form = self.parse_form(jep4_example2)
        self.check_form_iter(form, jep4_example2_fields)

    def test_jep4_example2_build_inc(self):
        form = self.build_form_inc("form", u"Bot Configuration",
                u"Fill out this form to configure your new bot!", jep4_example2_fields)
        self.check_form_info(form, jep4_example2_info)
        self.check_form_iter(form, jep4_example2_fields)

    def test_jep4_example2_build_direct(self):
        form = self.build_form_direct("form", u"Bot Configuration",
                u"Fill out this form to configure your new bot!", jep4_example2_fields)
        self.check_form_info(form, jep4_example2_info)
        self.check_form_iter(form, jep4_example2_fields)

    def test_jep4_example2_as_xml(self):
        form = self.build_form_inc("form", u"Bot Configuration",
                u"Fill out this form to configure your new bot!", jep4_example2_fields)
        xml = form.as_xml().serialize()
        form = self.parse_form(xml)
        self.check_form_info(form, jep4_example2_info)
        self.check_form_iter(form, jep4_example2_fields)

    def test_jep4_example2_make_submit(self):
        form = self.parse_form(jep4_example2)
        form['public'].value = True
        sform = form.make_submit()
        self.check_form_info(sform, ("submit", None, None))
        submitted_fields = [
                    (f[0], None, f[2], None, [], False, None)
                        for f in jep4_example2_fields
                            if f[1]!="fixed" and (f[5] or f[2])
                ]
        sform['public'].value = None
        self.check_form_iter(sform, submitted_fields)

    def test_jep4_example2_make_submit_with_types(self):
        form = self.parse_form(jep4_example2)
        form['public'].value = True
        sform = form.make_submit( keep_types = True )
        self.check_form_info(sform, ("submit", None, None))
        submitted_fields = [
                    (f[0], f[1], f[2], None, [], False, None)
                        for f in jep4_example2_fields
                            if f[1]!="fixed" and (f[5] or f[2])
                ]
        sform['public'].value = None
        self.check_form_iter(sform, submitted_fields)

    def test_jep4_example3_basic(self):
        form = self.parse_form(jep4_example3)
        self.check_form_info(form, jep4_example3_info)

    def test_jep4_example3_iter(self):
        form = self.parse_form(jep4_example3)
        self.check_form_iter(form, jep4_example3_fields)

    def test_jep4_example3_mapping(self):
        form = self.parse_form(jep4_example3)
        self.check_form_iter(form, jep4_example3_fields)

    def test_jep4_example3_parsed_values(self):
        form = self.parse_form(jep4_example3)
        self.check_form_parsed_values(form, jep4_example3_parsed_values)

    def test_jep4_example3_build_inc(self):
        form = self.build_form_inc("submit", None, None, jep4_example3_fields)
        self.check_form_info(form, jep4_example3_info)
        self.check_form_iter(form, jep4_example3_fields)

    def test_jep4_example3_build_direct(self):
        form = self.build_form_direct("submit", None, None, jep4_example3_fields)
        self.check_form_info(form, jep4_example3_info)
        self.check_form_iter(form, jep4_example3_fields)

    def test_jep4_example8_basic(self):
        form = self.parse_form(jep4_example8)
        self.check_form_info(form, jep4_example8_info)

    def test_jep4_example8_iter_items(self):
        form = self.parse_form(jep4_example8)
        self.check_form_iter(form, jep4_example8_fields)
        self.check_form_reported(form, jep4_example8_reported)
        self.check_form_items(form, jep4_example8_items)

    def test_field_text_hidden(self):
        field = Field(field_type="hidden", value=u"bleble")
        self.failUnlessEqual(field.value,u"bleble")
        self.failUnlessEqual(field.values,[u"bleble"])
        field = Field(field_type="hidden", values=[u"abcd"])
        self.failUnlessEqual(field.value,u"abcd")
        self.failUnlessEqual(field.values,[u"abcd"])
        field.value = u"zażółć gęślą jaźń"
        self.failUnlessEqual(field.value, u"zażółć gęślą jaźń")
        self.failUnlessEqual(field.values,[u"zażółć gęślą jaźń"])

    def test_field_text_fixed(self):
        field = Field(field_type="fixed", value=u"bleble")
        self.failUnlessEqual(field.value,u"bleble")
        self.failUnlessEqual(field.values,[u"bleble"])
        field = Field(field_type="fixed", values=[u"abcd"])
        self.failUnlessEqual(field.value,u"abcd")
        self.failUnlessEqual(field.values,[u"abcd"])
        field.value = u"zażółć gęślą jaźń"
        self.failUnlessEqual(field.value, u"zażółć gęślą jaźń")
        self.failUnlessEqual(field.values,[u"zażółć gęślą jaźń"])

    def test_field_text_private(self):
        field = Field(field_type="text-private", value=u"bleble")
        self.failUnlessEqual(field.value,u"bleble")
        self.failUnlessEqual(field.values,[u"bleble"])
        field = Field(field_type="text-private", values=[u"abcd"])
        self.failUnlessEqual(field.value,u"abcd")
        self.failUnlessEqual(field.values,[u"abcd"])
        field.value = u"zażółć gęślą jaźń"
        self.failUnlessEqual(field.value, u"zażółć gęślą jaźń")
        self.failUnlessEqual(field.values,[u"zażółć gęślą jaźń"])

    def test_field_text_single(self):
        field = Field(field_type="text-single", value=u"bleble")
        self.failUnlessEqual(field.value,u"bleble")
        self.failUnlessEqual(field.values,[u"bleble"])
        field = Field(field_type="text-single", values=[u"abcd"])
        self.failUnlessEqual(field.value,u"abcd")
        self.failUnlessEqual(field.values,[u"abcd"])
        field.value = u"zażółć gęślą jaźń"
        self.failUnlessEqual(field.value, u"zażółć gęślą jaźń")
        self.failUnlessEqual(field.values,[u"zażółć gęślą jaźń"])

    def test_field_text_multi(self):
        field = Field(field_type="text-multi", value=[u"item1", u"item2"])
        self.failUnlessEqual(field.value, [u"item1", u"item2"])
        self.failUnlessEqual(field.values, [u"item1", u"item2"])
        field = Field(field_type="text-multi", values=[u"item", u""])
        self.failUnlessEqual(field.value, [u"item", u""])
        self.failUnlessEqual(field.values, [u"item", u""])
        field.value = [u"a", u"b"]
        self.failUnlessEqual(field.value, [u"a", u"b"])
        self.failUnlessEqual(field.values, [u"a", u"b"])

    def test_field_list_single(self):
        field = Field(field_type="list-single", value=u"bleble")
        self.failUnlessEqual(field.value,u"bleble")
        self.failUnlessEqual(field.values,[u"bleble"])
        field = Field(field_type="list-single", values=[u"abcd"])
        self.failUnlessEqual(field.value,u"abcd")
        self.failUnlessEqual(field.values,[u"abcd"])
        field.value = u"zażółć gęślą jaźń"
        self.failUnlessEqual(field.value, u"zażółć gęślą jaźń")
        self.failUnlessEqual(field.values,[u"zażółć gęślą jaźń"])

    def test_field_list_multi(self):
        field = Field(field_type="list-multi", value=[u"item1", u"item2"])
        self.failUnlessEqual(field.value, [u"item1", u"item2"])
        self.failUnlessEqual(field.values, [u"item1", u"item2"])
        field = Field(field_type="list-multi", values=[u"item", u""])
        self.failUnlessEqual(field.value, [u"item", u""])
        self.failUnlessEqual(field.values, [u"item", u""])
        field.value = [u"a", u"b"]
        self.failUnlessEqual(field.value, [u"a", u"b"])
        self.failUnlessEqual(field.values, [u"a", u"b"])

    def test_field_jid_single(self):
        field = Field(field_type="jid-single", value=JID(u"user@example.com"))
        self.failUnlessEqual(field.value, JID(u"user@example.com"))
        self.failUnlessEqual(field.values, [u"user@example.com"])
        field = Field(field_type="jid-single", values=[u"user@example.com"])
        self.failUnlessEqual(field.value, JID(u"user@example.com"))
        self.failUnlessEqual(field.values, [u"user@example.com"])
        field.value = JID(u"example.com")
        self.failUnlessEqual(field.value, JID(u"example.com"))
        self.failUnlessEqual(field.values, [u"example.com"])

    def test_field_jid_multi(self):
        field = Field(field_type="jid-multi", value=[JID(u"user1@example.com"), JID(u"user2@example.com")])
        self.failUnlessEqual(field.value, [JID(u"user1@example.com"), JID(u"user2@example.com")])
        self.failUnlessEqual(field.values, [u"user1@example.com", u"user2@example.com"])
        field = Field(field_type="jid-multi", values=[u"user@example.com", u"example.com"])
        self.failUnlessEqual(field.value, [JID(u"user@example.com"), JID(u"example.com")])
        self.failUnlessEqual(field.values, [u"user@example.com", u"example.com"])
        field.value = [u"user3@example.com"]
        self.failUnlessEqual(field.value, [JID(u"user3@example.com")])
        self.failUnlessEqual(field.values, [u"user3@example.com"])

    def test_field_boolean(self):
        field = Field(field_type="boolean", value=True)
        self.failUnlessEqual(field.value, True)
        self.failUnlessEqual(field.values, [u"1"])
        field = Field(field_type="boolean", values=[u"0"])
        self.failUnlessEqual(field.value, False)
        self.failUnlessEqual(field.values, [u"0"])
        field.value = True
        self.failUnlessEqual(field.value, True)
        self.failUnlessEqual(field.values, [u"1"])

    def build_form_inc(self, form_type, title, instructions, field_data):
        form = Form(form_type)
        form.title = title
        form.instructions = instructions
        for name, ftype, values, label, options, required, desc in field_data:
            field = form.add_field(name = name, field_type = ftype, values = values,
                    label = label, required = required, desc = desc)
            for olabel, ovalue in options:
                field.add_option(ovalue, olabel)
        return form

    def build_form_direct(self, form_type, title, instructions, field_data):
        fields = []
        for name, ftype, values, label, options, required, desc in field_data:
            foptions = []
            for olabel, ovalue in options:
                foptions.append(Option(ovalue, olabel))
            field = Field(name = name, field_type = ftype, values = values,
                    label = label, options = foptions, required = required, desc = desc)
            fields.append(field)
        form = Form(form_type, title = title, instructions = instructions, fields = fields)
        return form

    def check_form_info(self, form, form_info):
        form_type, title, instructions = form_info
        self.failUnlessEqual(form.type, form_type)
        self.failUnlessEqual(form.title, title)
        self.failUnlessEqual(form.instructions, instructions)

    def check_form_iter(self, form, field_data):
        form_iter = iter(form)
        for name, ftype, values, label, options, required, desc in field_data:
            field = form_iter.next()
            self.failUnlessEqual(field.name, name)
            self.failUnlessEqual(field.type, ftype)
            self.failUnlessEqual(field.values, values)
            foptions = [(o.label, o.value) for o in field.options]
            self.failUnlessEqual(foptions, options)
            self.failUnlessEqual(field.required, required)
            self.failUnlessEqual(field.desc, desc)
        self.failUnlessRaises(StopIteration, form_iter.next)

    def check_form_mapping(self, form, field_data):
        for name, ftype, values, label, options, required, desc in field_data:
            if not name:
                continue
            field = form[name]
            self.failUnlessEqual(field.name, name)
            self.failUnlessEqual(field.type, ftype)
            self.failUnlessEqual(field.values, values)
            foptions = [(o.label, o.values[0]) for o in field.options]
            self.failUnlessEqual(foptions, options)
            self.failUnlessEqual(field.required, required)
            self.failUnlessEqual(field.desc, desc)

    def check_form_parsed_values(self, form, value_dict):
        for name, value in value_dict.items():
            field = form[name]
            self.failUnlessEqual(field.value,value)
            self.failUnless(type(field.value) is type(value))

    def check_form_reported(self, form, expected):
        it = iter(expected)
        for field in form.reported_fields:
            self.failUnlessEqual(field.name,it.next())
        self.failUnlessRaises(StopIteration, it.next)

    def check_form_items(self, form, items):
        it = iter(items)
        for item in form.items:
            self.check_form_iter(item, it.next())
        self.failUnlessRaises(StopIteration, it.next)

    def parse_form(self, xml):
        doc = libxml2.parseDoc(xml)
        root = doc.getRootElement()
        return Form(root)

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestForm))
     return suite

###################
# Test data follows

empty_form = """<x xmlns="jabber:x:data" type="form"/>"""
empty_submit = """<x xmlns="jabber:x:data" type="submit"/>"""
empty_cancel = """<x xmlns="jabber:x:data" type="cancel"/>"""
empty_result = """<x xmlns="jabber:x:data" type="result"/>"""

jep4_example2 = """
<x xmlns='jabber:x:data' type='form'>
  <title>Bot Configuration</title>
  <instructions>Fill out this form to configure your new bot!</instructions>
  <field type='hidden'
         var='FORM_TYPE'>
    <value>jabber:bot</value>
  </field>
  <field type='fixed'><value>Section 1: Bot Info</value></field>
  <field type='text-single'
         label='The name of your bot'
         var='botname'/>
  <field type='text-multi'
         label='Helpful description of your bot'
         var='description'/>
  <field type='boolean'
         label='Public bot?'
         var='public'>
    <required/>
  </field>
  <field type='text-private'
         label='Password for special access'
         var='password'/>
  <field type='fixed'><value>Section 2: Features</value></field>
  <field type='list-multi'
         label='What features will the bot support?'
         var='features'>
    <option label='Contests'><value>contests</value></option>
    <option label='News'><value>news</value></option>
    <option label='Polls'><value>polls</value></option>
    <option label='Reminders'><value>reminders</value></option>
    <option label='Search'><value>search</value></option>
  </field>
  <field type='fixed'><value>Section 3: Subscriber List</value></field>
  <field type='list-single'
         label='Maximum number of subscribers'
         var='maxsubs'>
    <value>20</value>
    <option label='10'><value>10</value></option>
    <option label='20'><value>20</value></option>
    <option label='30'><value>30</value></option>
    <option label='50'><value>50</value></option>
    <option label='100'><value>100</value></option>
    <option label='None'><value>none</value></option>
  </field>
  <field type='fixed'><value>Section 4: Invitations</value></field>
  <field type='jid-multi'
         label='People to invite'
         var='invitelist'>
    <desc>Tell all your friends about your new bot!</desc>
  </field>
</x>
"""
jep4_example2_info = (u"form", u"Bot Configuration", u"Fill out this form to configure your new bot!")
jep4_example2_fields = [
    # name, type, values, label, options, required, desc
    (u"FORM_TYPE", u"hidden", [u"jabber:bot"], None, [], False, None),
    (None, u"fixed", [u"Section 1: Bot Info"], None, [], False, None),
    ("botname", 'text-single', [], u'The name of your bot', [], False, None),
    ("description", "text-multi", [], u'Helpful description of your bot', [], False, None),
    ('public', 'boolean', [], u'Public bot?', [], True, None),
    ('password', 'text-private', [], u'Password for special access', [], False, None),
    (None, 'fixed', [u'Section 2: Features'], None, [], False, None),
    ('features', 'list-multi', [], u'What features will the bot support?', [
            (u'Contests', u'contests'),
            (u'News', u'news'),
            (u'Polls', u'polls'),
            (u'Reminders', u'reminders'),
            (u'Search', u'search'),
            ], False, None),
    (None, 'fixed', [u'Section 3: Subscriber List'], None, [], False, None),
    ('maxsubs', 'list-single', [u'20'], u'Maximum number of subscribers', [
            (u'10', u'10'),
            (u'20', u'20'),
            (u'30', u'30'),
            (u'50', u'50'),
            (u'100', u'100'),
            (u'None', u'none')], False, None),
    (None, 'fixed', [u'Section 4: Invitations'], None, [], False, None),
    ('invitelist', 'jid-multi', [], u'People to invite', [], False, u'Tell all your friends about your new bot!'),
    ]
jep4_example2_reported = []
jep4_example2_items = []

jep4_example3 = """
<x xmlns='jabber:x:data' type='submit'>
  <field type='hidden' var='FORM_TYPE'>
    <value>jabber:bot</value>
  </field>
  <field type='text-single' var='botname'>
    <value>The Jabber Google Bot</value>
  </field>
  <field type='text-multi' var='description'>
    <value>This bot enables you to send requests to</value>
    <value>Google and receive the search results right</value>
    <value>in your Jabber client. It&apos; really cool!</value>
    <value>It even supports Google News!</value>
  </field>
  <field type='boolean' var='public'>
    <value>0</value>
  </field>
  <field type='text-private' var='password'>
    <value>v3r0na</value>
  </field>
  <field type='list-multi' var='features'>
    <value>news</value>
    <value>search</value>
  </field>
  <field type='list-single' var='maxsubs'>
    <value>50</value>
  </field>
  <field type='jid-multi' var='invitelist'>
    <value>juliet@capulet.com</value>
    <value>benvolio@montague.net</value>
  </field>
</x>
"""
jep4_example3_info = ("submit", None, None)
jep4_example3_fields = [
    # name, type, values, label, options, required, desc
    ('FORM_TYPE', 'hidden', ['jabber:bot'], None, [], False, None),
    ('botname', 'text-single', [u'The Jabber Google Bot'], None, [], False, None),
    ('description', 'text-multi', [u'This bot enables you to send requests to',
        u'Google and receive the search results right',
        u'in your Jabber client. It\' really cool!',
        u'It even supports Google News!'], None, [], False, None),
    ('public', 'boolean', [u'0'], None, [], False, None),
    ('password', 'text-private', [u'v3r0na'],  None, [], False, None),
    ('features', 'list-multi', [u'news', u'search'], None, [], False, None),
    ('maxsubs', 'list-single', [u'50'], None, [], False, None),
    ('invitelist', 'jid-multi', [u'juliet@capulet.com', u'benvolio@montague.net'], None, [], False, None),
    ]
jep4_example3_reported = []
jep4_example3_items = []
jep4_example3_parsed_values = {
    'FORM_TYPE': u'jabber:bot',
    'botname': u'The Jabber Google Bot',
    'description': [u'This bot enables you to send requests to',
            u'Google and receive the search results right',
            u'in your Jabber client. It\' really cool!',
            u'It even supports Google News!'],
    'public': False,
    'password': u'v3r0na',
    'features': [u'news', u'search'],
    'maxsubs': u'50',
    'invitelist': [JID(u'juliet@capulet.com'), JID(u'benvolio@montague.net')],
    }

jep4_example8 = """
<x xmlns='jabber:x:data' type='result'>
  <title>Joogle Search: verona</title>
  <reported>
    <field var='name'/>
    <field var='url'/>
  </reported>
  <item>
    <field var='name'>
      <value>Comune di Verona - Benvenuti nel sito ufficiale</value>
    </field>
    <field var='url'>
      <value>http://www.comune.verona.it/</value>
    </field>
  </item>
  <item>
    <field var='name'>
      <value>benvenuto!</value>
    </field>
    <field var='url'>
      <value>http://www.hellasverona.it/</value>
    </field>
  </item>
  <item>
    <field var='name'>
      <value>Universita degli Studi di Verona - Home Page</value>
    </field>
    <field var='url'>
      <value>http://www.univr.it/</value>
    </field>
  </item>
  <item>
    <field var='name'>
      <value>Aeroporti del Garda</value>
    </field>
    <field var='url'>
      <value>http://www.aeroportoverona.it/</value>
    </field>
  </item>
  <item>
    <field var='name'>
      <value>Veronafiere - fiera di Verona</value>
    </field>
    <field var='url'>
      <value>http://www.veronafiere.it/</value>
    </field>
  </item>
</x>
"""
jep4_example8_info = ("result", "Joogle Search: verona", None)
jep4_example8_fields = []
jep4_example8_reported = ["name", "url"]
jep4_example8_items = [
                # name, type, values, label, options, required, desc
        [
            ("name", None, ['Comune di Verona - Benvenuti nel sito ufficiale'],
                    None, [], False, None),
            ("url", None, ['http://www.comune.verona.it/'],
                    None, [], False, None),
        ],
        [
            ("name", None, ['benvenuto!'],
                    None, [], False, None),
            ("url", None, ['http://www.hellasverona.it/'],
                    None, [], False, None),
        ],
        [
            ("name", None, ['Universita degli Studi di Verona - Home Page'],
                    None, [], False, None),
            ("url", None, ['http://www.univr.it/'],
                    None, [], False, None),
        ],
        [
            ("name", None, ['Aeroporti del Garda'],
                    None, [], False, None),
            ("url", None, ['http://www.aeroportoverona.it/'],
                    None, [], False, None),
        ],
        [
            ("name", None, ['Veronafiere - fiera di Verona'],
                    None, [], False, None),
            ("url", None, ['http://www.veronafiere.it/'],
                    None, [], False, None),
        ],

    ]

# end of test data
###################

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
