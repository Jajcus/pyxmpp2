#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import libxml2
from pyxmpp2.jabber.dataforms import Form, Field, Option
from pyxmpp2.jabber.register import Register, REGISTER_NS
from pyxmpp2.iq import Iq

legacy_fields = ( "username", "nick", "password", "name", "first", "last", "email", "address",
        "city", "state", "zip", "phone", "url", "date", "misc", "text", "key" )

class TestRegister(unittest.TestCase):
    def test_jep77_example1(self):
        register = self.parse_stanza(jep77_example1)
        self.assertTrue(register.form is None)
        self.assertFalse(register.registered)
        self.assertTrue(register.instructions is None)
        self.assertFalse(register.remove)
        for field in legacy_fields:
            self.assertTrue(getattr(register, field) is None)
    def test_jep77_example2(self):
        register = self.parse_stanza(jep77_example2)
        self.assertEqual(register.instructions.strip(), u"Choose a username and password for use with this service.\n       Please also provide your email address.")
        self.assertEqual(register.username, u"")
        self.assertEqual(register.password, u"")
        self.assertEqual(register.email, u"")

    def test_jep77_example2_get_form(self):
        register = self.parse_stanza(jep77_example2)
        form = register.get_form()
        self.assertEqual(form["FORM_TYPE"].value, "jabber:iq:register")
        self.assertEqual(form.instructions.strip(), u"Choose a username and password for use with this service.\n       Please also provide your email address.")
        self.assertTrue("username" in form)
        self.assertTrue(form["username"].required)
        self.assertTrue("password" in form)
        self.assertTrue(form["password"].required)
        self.assertTrue("email" in form)
        self.assertTrue(form["email"].required)

    def test_jep77_example3(self):
        register = self.parse_stanza(jep77_example3)
        self.assertTrue(register.registered)
        self.assertEqual(register.username, u"juliet")
        self.assertEqual(register.password, u"R0m30")
        self.assertEqual(register.email, u"juliet@capulet.com")
    def test_jep77_example4(self):
        register = self.parse_stanza(jep77_example4)
        self.assertFalse(register.registered)
        self.assertEqual(register.username, u"bill")
        self.assertEqual(register.password, u"Calliope")
        self.assertEqual(register.email, u"bill@shakespeare.lit")
    def test_jep77_example8(self):
        register = self.parse_stanza(jep77_example8)
        self.assertTrue(register.remove)
    def test_jep77_example10(self):
        register = self.parse_stanza(jep77_example10)
        self.assertEqual(register.username, u"bill")
        self.assertEqual(register.password, u"newpass")
    def test_jep77_example16(self):
        register = self.parse_stanza(jep77_example16)
        form = self.parse_form(jep77_example16_form)
        self.assertFalse(register.form is None)
        self.assertEqual(register.form.type, form.type)
        self.assertEqual(register.form.instructions, form.instructions)
        self.assertEqual(len(register.form.fields), len(form.fields))
        for i in range(0, len(form.fields)):
            f1 = register.form[i]
            f2 = form[i]
            self.assertEqual(f1.name, f2.name)
            self.assertEqual(f1.type, f2.type)
            self.assertEqual(f1.value, f2.value)

    def test_jep77_example17(self):
        register = self.parse_stanza(jep77_example17)
        self.assertEqual(register.instructions.strip(), u"To register, visit http://www.shakespeare.lit/contests.php")

    def parse_stanza(self, xml):
        doc = libxml2.parseDoc(xml)
        root = doc.getRootElement()
        iq = Iq(root)
        register = iq.get_query()
        return Register(register)

    def parse_form(self, xml):
        doc = libxml2.parseDoc(xml)
        root = doc.getRootElement()
        return Form(root)

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestRegister))
     return suite

###################
# Test data follows

jep77_example1 = """
 <iq type='get' id='reg1'>
   <query xmlns='jabber:iq:register'/>
 </iq>
"""

jep77_example2 = """
 <iq type='result' id='reg1'>
   <query xmlns='jabber:iq:register'>
     <instructions>
       Choose a username and password for use with this service.
       Please also provide your email address.
     </instructions>
     <username/>
     <password/>
     <email/>
   </query>
 </iq>
"""

jep77_example3 = """
 <iq type='result' id='reg1'>
   <query xmlns='jabber:iq:register'>
     <registered/>
     <username>juliet</username>
     <password>R0m30</password>
     <email>juliet@capulet.com</email>
   </query>
 </iq>
"""

jep77_example4 = """
 <iq type='set' id='reg2'>
   <query xmlns='jabber:iq:register'>
     <username>bill</username>
     <password>Calliope</password>
     <email>bill@shakespeare.lit</email>
   </query>
 </iq>
"""

jep77_example8 = """
 <iq type='set' from='bill@shakespeare.lit/globe' id='unreg1'>
   <query xmlns='jabber:iq:register'>
     <remove/>
   </query>
 </iq>
"""

jep77_example10 = """
 <iq type='set' to='somehost' id='change1'>
   <query xmlns='jabber:iq:register'>
     <username>bill</username>
     <password>newpass</password>
   </query>
 </iq>
"""

jep77_example16 = """
 <iq type='result'
     from='contests.shakespeare.lit'
     to='juliet@capulet.com/balcony'
     id='reg3'>
   <query xmlns='jabber:iq:register'>
     <instructions>
       Use the enclosed form to register. If your Jabber client does not
       support Data Forms, visit http://www.shakespeare.lit/contests.php
     </instructions>
     <x xmlns='jabber:x:data' type='form'>
       <title>Contest Registration</title>
       <instructions>
         Please provide the following information
         to sign up for our special contests!
       </instructions>
       <field
           type='hidden'
           var='FORM_TYPE'>
         <value>jabber:iq:register</value>
       </field>
       <field
           type='text-single'
           label='Given Name'
           var='first'>
         <required/>
       </field>
       <field
           type='text-single'
           label='Family Name'
           var='last'>
         <required/>
       </field>
       <field
           type='text-single'
           label='Email Address'
           var='email'>
         <required/>
       </field>
       <field
           type='list-single'
           label='Gender'
           var='x-gender'>
         <option label='Male'><value>M</value></option>
         <option label='Female'><value>F</value></option>
       </field>
     </x>
   </query>
 </iq>
"""

jep77_example16_form = """
     <x xmlns='jabber:x:data' type='form'>
       <title>Contest Registration</title>
       <instructions>
         Please provide the following information
         to sign up for our special contests!
       </instructions>
       <field
           type='hidden'
           var='FORM_TYPE'>
         <value>jabber:iq:register</value>
       </field>
       <field
           type='text-single'
           label='Given Name'
           var='first'>
         <required/>
       </field>
       <field
           type='text-single'
           label='Family Name'
           var='last'>
         <required/>
       </field>
       <field
           type='text-single'
           label='Email Address'
           var='email'>
         <required/>
       </field>
       <field
           type='list-single'
           label='Gender'
           var='x-gender'>
         <option label='Male'><value>M</value></option>
         <option label='Female'><value>F</value></option>
       </field>
     </x>
"""

jep77_example17 = """
 <iq type='result'
     from='contests.shakespeare.lit'
     to='juliet@capulet.com/balcony'
     id='reg3'>
   <query xmlns='jabber:iq:register'>
     <instructions>
       To register, visit http://www.shakespeare.lit/contests.php
     </instructions>
   </query>
   <x xmlns='jabber:x:oob'>
     <url>http://www.shakespeare.lit/contests.php</url>
   </x>
 </iq>
"""

# end of test data
###################

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
