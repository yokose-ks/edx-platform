"""
Tests for the Split Testing Module
"""

from mock import Mock
from django.test import TestCase
from xmodule.tests import get_test_system
from xmodule.split_test_module import SplitTestModule, SplitTestDescriptor


class SplitTestModuleTest(TestCase):
    """
    Test the split test module
    """

    def setUp(self):
        self.course_id = 'test_org/test_course_number/test_run'
        self.system = get_test_system(self.course_id)
        # construct module

        self.split_test_module_descriptor = SplitTestDescriptor()

        test_xml = """
            <split_test url_name="split1" user_partition_id="0" group_id_to_child='{"0": "i4x://MITx/6.00x/html/split_test_cond0", "1": "i4x://MITx/6.00x/html/split_test_cond1"}'>
                <html url_name="split_test_cond0">condition 0</html>
                <html url_name="split_test_cond1">condition 1</html>
            </split_test>
        """
        mock_id_generator = Mock()
        self.split_test_module_descriptor.from_xml(test_xml, self.system, mock_id_generator)
        self.split_test_module = SplitTestModule(self.split_test_module_descriptor)
