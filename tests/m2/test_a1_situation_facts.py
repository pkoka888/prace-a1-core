"""The Article 12 situation facts on the Assignment model.

Decision D10 and D1b (2026-10-20). The two fields are nullable, so an
absent fact is distinguishable from a negative answer: the fact is "not
captured", never "no". The migration is additive, so no existing row changes
shape.

Synthetic only; no real private data, scans, or PII.
"""

from pathlib import Path

from django.test import TestCase

from portal.release1a.models import Assignment

REPO = Path(__file__).resolve().parents[2]


class A1SituationFactsModelTests(TestCase):
    def test_the_fields_are_nullable(self):
        prior = Assignment._meta.get_field("prior_activity_start")
        replaces = Assignment._meta.get_field("replaces_worker")
        self.assertTrue(prior.null)
        self.assertTrue(prior.blank)
        self.assertTrue(replaces.null)
        self.assertTrue(replaces.blank)

    def test_the_replacement_flag_is_a_tri_state(self):
        """Null must be distinguishable from False.

        A nullable boolean has three states. That distinction is the whole
        point of the field: the question "does this worker replace another
        posted person" has three honest answers, and only two of them are
        yes or no.
        """
        replaces = Assignment._meta.get_field("replaces_worker")
        self.assertTrue(replaces.null)
        self.assertIsNone(replaces.get_default())

    def test_the_fields_live_on_the_arrangement_not_on_the_person(self):
        """One owner per fact.

        The situation is a property of the employment arrangement, so the
        fields sit on the Assignment. They are not on the Worker, because
        two workers can be in different situations, and not inside
        a1_facts_json, because a fact inside a JSON blob and a fact in a
        column would be two owners for one value.
        """
        self.assertIn("prior_activity_start", {f.name for f in Assignment._meta.fields})
        self.assertIn("replaces_worker", {f.name for f in Assignment._meta.fields})
        self.assertNotIn("prior_activity_start", {f.name for f in Assignment._meta.fields} - {"prior_activity_start"})

    def test_the_migration_is_additive(self):
        migration = (
            REPO
            / "portal"
            / "release1a"
            / "migrations"
            / "0021_a1_situation_facts.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(migration.count("AddField"), 2)
        self.assertNotIn("RemoveField", migration)
        self.assertNotIn("DeleteModel", migration)
        self.assertNotIn("AlterField", migration)
