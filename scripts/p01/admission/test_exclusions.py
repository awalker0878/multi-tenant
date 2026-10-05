import unittest
from exclusions import check_added_suppressions
from policy import Denied, required_roles


class ExclusionTests(unittest.TestCase):
    def test_added_and_broadened_suppressions_are_denied(self):
        for before,after in [('', 'value = bad() # type: ignore'),
                             ('# noqa: E501', '# noqa'), ('', '// @ts-nocheck'), ('', '// @phpstan-ignore-next-line')]:
            with self.assertRaisesRegex(Denied, '^unapproved_inline_suppression:'):
                check_added_suppressions('services/planning/src/a.py', before, after, [], 'a'*40)

    def test_removal_is_allowed(self):
        check_added_suppressions('services/planning/src/a.py', '# noqa', '', [], 'a'*40)

    def test_exception_must_match_exact_source_and_file(self):
        e={'kind':'type-analysis','rule_id':'inline-type-suppression','paths':['services/planning/src/a.py'],'source_revision':'a'*40}
        check_added_suppressions(e['paths'][0], '', '# noqa', [e], 'a'*40)
        with self.assertRaises(Denied):check_added_suppressions(e['paths'][0], '', '# noqa', [e], 'b'*40)
        with self.assertRaises(Denied):check_added_suppressions('services/planning/src/b.py', '', '# noqa', [e], 'a'*40)

    def test_configuration_changes_require_security_and_platform(self):
        for path in ['services/planning/pyproject.toml','apps/console/tsconfig.json','services/catalogue/phpstan.neon']:
            self.assertTrue({'security','platform'} <= required_roles([path], ['planning']))


if __name__ == '__main__':unittest.main()
