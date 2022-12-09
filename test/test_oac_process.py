import unittest
import filecmp
import codecs
from aspace_tools import oac_process


class TestOACProcess(unittest.TestCase):

    def process_test_file(self, input_path, output_path):
        finding_aid = oac_process.FindingAid(input_path, False, True, True)
        finding_aid.process()
        with codecs.open(output_path, 'w', 'utf-8') as outfile:
            outfile.write(finding_aid.new_xml)

    def test_simple_ead(self):
        # ms040
        input_path = "test_data/MS.040_20221209_222733_UTC__ead.xml"
        output_path = "test_data/test_out_001.xml"
        compare_path = "test_data/ms040.xml"
        self.process_test_file(input_path, output_path)
        assert filecmp.cmp(output_path, compare_path, shallow=False)


    # def ead_with_title_emph(self):
    #     # ms306

    # def ead_with_digital_object(self):
    #     # ua392



if __name__ == '__main__':
    unittest.main()
