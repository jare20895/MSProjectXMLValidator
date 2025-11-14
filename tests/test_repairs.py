import unittest
import xml.etree.ElementTree as ET

from msproject_validator.repairs import detect_circular_dependencies, fix_summary_task_predecessors


class TestRepairs(unittest.TestCase):
    def test_detect_circular_dependencies_removes_links(self):
        xml = '''<?xml version="1.0"?>
        <Project xmlns="http://schemas.microsoft.com/project">
          <Tasks>
            <Task>
              <UID>1</UID>
              <Name>A</Name>
              <PredecessorLink><PredecessorUID>2</PredecessorUID></PredecessorLink>
            </Task>
            <Task>
              <UID>2</UID>
              <Name>B</Name>
              <PredecessorLink><PredecessorUID>1</PredecessorUID></PredecessorLink>
            </Task>
          </Tasks>
        </Project>
        '''
        root = ET.fromstring(xml)
        errors = {}
        repairs = {}
        found = detect_circular_dependencies(root, errors, repairs)
        # function should detect a cycle and return True
        self.assertTrue(found)
        # after repair, tasks should have no PredecessorLink children
        preds = root.findall('.//{http://schemas.microsoft.com/project}PredecessorLink')
        self.assertEqual(len(preds), 0)
        # repairs should have an entry for Circular Dependencies
        self.assertIn('Circular Dependencies', repairs)

    def test_fix_summary_task_predecessors_moves_links(self):
        xml = '''<?xml version="1.0"?>
        <Project xmlns="http://schemas.microsoft.com/project">
          <Tasks>
            <Task>
              <UID>99</UID>
              <Name>Prev</Name>
            </Task>
            <Task>
              <UID>100</UID>
              <Name>Summary</Name>
              <Summary>1</Summary>
              <OutlineLevel>1</OutlineLevel>
              <PredecessorLink><PredecessorUID>99</PredecessorUID><Type>1</Type></PredecessorLink>
            </Task>
            <Task>
              <UID>101</UID>
              <Name>Child</Name>
              <OutlineLevel>2</OutlineLevel>
            </Task>
          </Tasks>
        </Project>
        '''
        root = ET.fromstring(xml)
        repairs = {}
        fix_summary_task_predecessors(root, repairs)
        # Summary should have no PredecessorLink now
        summary_preds = root.findall('.//{http://schemas.microsoft.com/project}Task[{http://schemas.microsoft.com/project}Summary="1"]//{http://schemas.microsoft.com/project}PredecessorLink')
        self.assertEqual(len(summary_preds), 0)
        # Child should now have the PredecessorLink moved to it
        child_preds = root.findall('.//{http://schemas.microsoft.com/project}Task[{http://schemas.microsoft.com/project}UID="101"]//{http://schemas.microsoft.com/project}PredecessorLink')
        self.assertEqual(len(child_preds), 1)
        pred_uid = child_preds[0].find('{http://schemas.microsoft.com/project}PredecessorUID')
        self.assertIsNotNone(pred_uid)
        self.assertEqual(pred_uid.text, '99')
        # repairs should show Summary Task Dependencies
        self.assertIn('Summary Task Dependencies', repairs)


if __name__ == '__main__':
    unittest.main()
