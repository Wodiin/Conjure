import unittest
from data_loader import data

class TestDataLoader(unittest.TestCase):

    def test_files_loaded(self):
        """Check all expected files are loaded"""
        expected = [
            'base_categories', 'races', 'environments',
            'names', 'personalities', 'weapons',
            'combat_kits', 'magic_kits', 'role_kits'
        ]
        for file in expected:
            self.assertIn(file, data, f"Missing: {file}")

    def test_files_not_empty(self):
        """Check no file loaded as empty"""
        for key, value in data.items():
            self.assertTrue(value, f"{key} is empty")

    def test_races_loaded(self):
        """Spot check races has content"""
        self.assertIn('races', data)
        self.assertGreater(len(data['races']), 0)

    def test_kits_loaded(self):
        """Spot check kits have content"""
        for kit in ['combat_kits', 'magic_kits', 'role_kits']:
            self.assertGreater(len(data[kit]), 0, f"{kit} is empty")

if __name__ == '__main__':
    unittest.main(verbosity=2)