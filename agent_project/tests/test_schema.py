import unittest
from core.schema import ALLOWED_REVIEW_CODES
class TestSchema(unittest.TestCase):
    def test_review_codes_unique(self):
        self.assertEqual(len(ALLOWED_REVIEW_CODES),len(set(ALLOWED_REVIEW_CODES)))
if __name__=='__main__': unittest.main()
