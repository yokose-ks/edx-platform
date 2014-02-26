"""
Tests for the Split Testing Module
"""

from xmodule.tests.xml import factories as xml
from xmodule.split_test_module import SplitTestModule
from xmodule.tests.xml import XModuleXmlImportTest


class SplitTestModuleFactory(xml.XmlImportFactory):
    """
    Factory for generating SplitTestModules for testing purposes
    """
    tag = 'split_test'


class SplitTestModuleTest(XModuleXmlImportTest):
    """
    Test the split test module
    """

    def setUp(self):
        self.course_id = 'test_org/test_course_number/test_run'
        # construct module

        course = xml.CourseFactory.build()
        sequence = xml.SequenceFactory.build(parent=course)
        split_test = SplitTestModuleFactory(
            parent=sequence,
            attribs={
                'user_partition_id': '0',
                'group_id_to_child': '{"0": "html/split_test_cond0", "1": "html/split_test_cond1"}'
            }
        )
        xml.HtmlFactory(parent=split_test, url_name='split_test_cond0')
        xml.HtmlFactory(parent=split_test, url_name='split_test_cond1')

        self.course = self.process_xml(course)
        course_seq = self.course.get_children()[0]
        self.split_test_descriptor = course_seq.get_children()[0]

    def test_creation(self):
        print type(self.split_test_descriptor)
        self.assertTrue(type(self.split_test_descriptor) is SplitTestModule)
