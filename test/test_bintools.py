import unittest
import sys
import io
from unittest.mock import patch
from ppci.target.arm.instructions import ArmToken
from ppci.binutils.objectfile import ObjectFile, serialize, deserialize
from ppci.binutils.objectfile import load_object
from ppci.binutils.outstream import DummyOutputStream, TextOutputStream
from ppci.tasks import TaskError
from ppci.buildfunctions import link
from ppci.binutils import layout
from ppci.target.example import Mov, R0, R1


class TokenTestCase(unittest.TestCase):
    def testSetBits(self):
        at = ArmToken()
        at[2:4] = 0b11
        self.assertEqual(0xc, at.bit_value)

    def testSetBits2(self):
        at = ArmToken()
        at[4:8] = 0b1100
        self.assertEqual(0xc0, at.bit_value)


class OutstreamTestCase(unittest.TestCase):
    def test_dummy_stream(self):
        stream = DummyOutputStream()
        stream.select_section('code')
        stream.emit(Mov(R1, R0))

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_text_stream(self, mock_stdout):
        stream = TextOutputStream()
        stream.select_section('code')
        stream.emit(Mov(R1, R0))


class LinkerTestCase(unittest.TestCase):
    def testUndefinedReference(self):
        o1 = ObjectFile()
        o1.get_section('.text')
        o1.add_relocation('undefined_sym', 0, 'rel8', '.text')
        o2 = ObjectFile()
        with self.assertRaises(TaskError):
            link([o1, o2], layout.Layout(), 'arm')

    def testDuplicateSymbol(self):
        o1 = ObjectFile()
        o1.get_section('.text')
        o1.add_symbol('a', 0, '.text')
        o2 = ObjectFile()
        o2.get_section('.text')
        o2.add_symbol('a', 0, '.text')
        with self.assertRaises(TaskError):
            link([o1, o2], layout.Layout(), 'arm')

    def testRel8Relocation(self):
        o1 = ObjectFile()
        o1.get_section('.text').add_data(bytes([0]*100))
        o1.add_relocation('a', 0, 'rel8', '.text')
        o2 = ObjectFile()
        o2.get_section('.text').add_data(bytes([0]*100))
        o2.add_symbol('a', 24, '.text')
        link([o1, o2], layout.Layout(), 'arm')

    def testSymbolValues(self):
        o1 = ObjectFile()
        o1.get_section('.text').add_data(bytes([0]*108))
        o1.add_symbol('b', 24, '.text')
        o2 = ObjectFile()
        o2.get_section('.text').add_data(bytes([0]*100))
        o2.add_symbol('a', 2, '.text')
        o3 = link([o1, o2], layout.Layout(), 'arm')
        self.assertEqual(110, o3.find_symbol('a').value)
        self.assertEqual(24, o3.find_symbol('b').value)
        self.assertEqual(208, o3.get_section('.text').Size)

    def testMemoryLayout(self):
        spec = """
            MEMORY flash LOCATION=0x08000000 SIZE=0x3000 {
              SECTION(code)
            }
            MEMORY flash LOCATION=0x20000000 SIZE=0x3000 {
              SECTION(data)
            }
        """
        memory_layout = layout.load_layout(io.StringIO(spec))
        o1 = ObjectFile()
        o1.get_section('code').add_data(bytes([0]*108))
        o1.add_symbol('b', 24, 'code')
        o2 = ObjectFile()
        o2.get_section('code').add_data(bytes([0]*100))
        o2.get_section('data').add_data(bytes([0]*100))
        o2.add_symbol('a', 2, 'data')
        o2.add_symbol('c', 2, 'code')
        o3 = link([o1, o2], memory_layout, 'arm')
        self.assertEqual(0x20000000+2, o3.get_symbol_value('a'))
        self.assertEqual(0x08000000+24, o3.get_symbol_value('b'))
        self.assertEqual(0x08000000+110, o3.get_symbol_value('c'))
        self.assertEqual(208, o3.get_section('code').Size)
        self.assertEqual(100, o3.get_section('data').Size)


class ObjectFileTestCase(unittest.TestCase):
    def makeTwins(self):
        o1 = ObjectFile()
        o2 = ObjectFile()
        o2.get_section('code').add_data(bytes(range(55)))
        o1.get_section('code').add_data(bytes(range(55)))
        o1.add_relocation('A', 0x2, 'imm12_dumm', 'code')
        o2.add_relocation('A', 0x2, 'imm12_dumm', 'code')
        o1.add_symbol('A2', 0x90, 'code')
        o2.add_symbol('A2', 0x90, 'code')
        o1.add_symbol('A3', 0x90, 'code')
        o2.add_symbol('A3', 0x90, 'code')
        o1.add_image('a', 0x0, bytes([1, 2, 3]))
        o2.add_image('a', 0x0, bytes([1, 2, 3]))
        return o1, o2

    def testEquality(self):
        o1, o2 = self.makeTwins()
        self.assertEqual(o1, o2)

    def testSaveAndLoad(self):
        o1, o2 = self.makeTwins()
        f1 = io.StringIO()
        o1.save(f1)
        f2 = io.StringIO(f1.getvalue())
        o3 = load_object(f2)
        self.assertEqual(o3, o1)

    def testSerialization(self):
        o1, o2 = self.makeTwins()
        o3 = deserialize(serialize(o1))
        self.assertEqual(o3, o1)


class LayoutFileTestCase(unittest.TestCase):
    def testLayout1(self):
        spec = """
            MEMORY flash LOCATION=0x1000 SIZE=0x3000 {
              SECTION(code)
              ALIGN(4)
            }
        """
        layout1 = layout.load_layout(io.StringIO(spec))
        layout2 = layout.Layout()
        m = layout.Memory('flash')
        m.location = 0x1000
        m.size = 0x3000
        m.add_input(layout.Section('code'))
        m.add_input(layout.Align(4))
        layout2.add_memory(m)
        self.assertEqual(layout2, layout1)


if __name__ == '__main__':
    unittest.main()
    sys.exit()
