"""Guard the actual final policy sections recorded by the 1.15 migration audit."""
import hashlib
import json
from pathlib import Path
import re
import unittest


class PolicyMigrationTests(unittest.TestCase):
    def test_final_section_hashes(self):
        root = Path(__file__).resolve().parents[1]
        audit = json.loads((root / 'instructions/policy-migration-1.15.0.json').read_text())
        names = [entry['heading'] for entry in audit['sections']]
        self.assertEqual(len(names), len(set(names)))
        for entry in audit['sections']:
            with self.subTest(heading=entry['heading']):
                parts = re.split(r'(?m)^## ', (root / entry['destination']).read_text())
                sections = {part.split('\n', 1)[0]: '## ' + part for part in parts[1:]}
                text = sections[entry['heading']].rstrip() + '\n'
                self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), entry['migrated_sha256'])


if __name__ == '__main__':
    unittest.main()
