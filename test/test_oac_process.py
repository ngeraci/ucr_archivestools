""" test the FindingAid.process function from oac_process.py:
    compare xml output to a known good version (compare_path)
"""

import unittest
import os
import filecmp
import codecs
from aspace_tools import oac_process

OUTPUT_PATH = "test/test_data/test.xml"


class TestOACProcess(unittest.TestCase):
    def process_test_file(self, input_path):
        finding_aid = oac_process.FindingAid(input_path, False, True, True)
        finding_aid.process()
        with codecs.open(OUTPUT_PATH, 'w', 'utf-8') as outfile:
            outfile.write(finding_aid.new_xml)

    def test_simple_ead(self):
        # ms040
        input_path = "test/test_data/MS.040_20221209_222733_UTC__ead.xml"
        compare_path = "test/test_data/ms040.xml"
        self.process_test_file(input_path)
        assert filecmp.cmp(OUTPUT_PATH, compare_path, shallow=False)

    def test_ead_with_title_emph(self):
        # ms306
        input_path = "test/test_data/MS.306_20221209_222940_UTC__ead.xml"
        compare_path = "test/test_data/ms306.xml"
        self.process_test_file(input_path)
        assert filecmp.cmp(OUTPUT_PATH, compare_path, shallow=False)

    def test_ead_with_digital_object(self):
        # ua392
        input_path = "test/test_data/UA.392_20221209_223010_UTC__ead.xml"
        compare_path = "test/test_data/ua392.xml"
        self.process_test_file(input_path)
        assert filecmp.cmp(OUTPUT_PATH, compare_path, shallow=False)

    def tearDown(self):
        """ delete "test.xml" after running test
        """
        os.remove(OUTPUT_PATH)


if __name__ == '__main__':
    unittest.main()
