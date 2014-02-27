"""
Tests for the Split Testing Module
"""
import ddt
from mock import Mock

from xmodule.tests.xml import factories as xml
from xmodule.tests.xml import XModuleXmlImportTest
from xmodule.split_test_module import SplitTestModule
from xmodule.tests import get_test_system
from xmodule.partitions.partitions import Group, UserPartition

class SplitTestModuleFactory(xml.XmlImportFactory):
    """
    Factory for generating SplitTestModules for testing purposes
    """
    tag = 'split_test'


@ddt.ddt
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
        self.module_system = get_test_system()
        self.module_system.user_partitions = [
            UserPartition(0, 'first_partition', 'First Partition', [Group("0", 'alpha'), Group("1", 'beta')]),
            UserPartition(1, 'second_partition', 'Second Partition', [Group("0", 'abel'), Group("1", 'baker'), Group("2", 'charlie')])
        ]
        self.module_system.user_service = Mock(name='user_service')
        self.split_test_descriptor = course_seq.get_children()[0]
        self.split_test_descriptor.bind_for_student(
            self.module_system,
            self.split_test_descriptor._field_data
        )

    @ddt.data(('0', 'split_test_cond0'), ('1', 'split_test_cond1'))
    @ddt.unpack
    def test_child(self, user_tag, child_url_name):
        self.module_system.user_service.get_tag.return_value = user_tag

        self.assertEquals(self.split_test_descriptor.child_descriptor.url_name, child_url_name)
