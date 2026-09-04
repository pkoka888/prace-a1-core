"""Regression coverage for the invitation-only authentication surface."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")

import django

django.setup()

from allauth.account.adapter import get_adapter
from django.test import RequestFactory, SimpleTestCase


class AuthenticationUiTests(SimpleTestCase):
    def test_login_uses_portal_shell_and_does_not_offer_signup(self):
        response = self.client.get("/accounts/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "portal/tailwind-2.2.19.min.css")
        self.assertContains(response, "Přístup je pouze pro pozvané recenzenty")
        self.assertNotContains(response, "Zaregistrovat se")

    def test_anonymous_portal_has_no_fake_user_identity_or_navigation(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nepřihlášen")
        self.assertNotContains(response, "Jan Novak")
        self.assertNotContains(response, ">Pracovníci<")

    def test_signup_is_closed_by_account_adapter(self):
        request = RequestFactory().get("/accounts/signup/")

        self.assertFalse(get_adapter(request).is_open_for_signup(request))

        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "portal/tailwind-2.2.19.min.css")
        self.assertNotContains(response, "<form")
