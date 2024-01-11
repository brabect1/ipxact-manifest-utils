# Copyright 2024 Tomas Brabec
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import os
import sys
import verible_verilog_syntax

# add required source code into PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.vlog2ipxact import Port, get_ports

class TestVlogGetPorts(unittest.TestCase):

    def parse_verilog(self, vlogSyntax):
        parser_path='verible-verilog-syntax';
        parser = verible_verilog_syntax.VeribleVerilogSyntax(executable=parser_path);
        data = parser.parse_string(vlogSyntax);
        return data;

    def test_single_undirected_untyped_scalar(self):
        data = '''
        module foo(
            a
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'a', 'type': None, 'dir': 'in'};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_undirected_typed_scalar(self):
        data = '''
        module foo(
            logic bar
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'bar', 'type': 'logic', 'dir': 'in'};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_undirected_typed_vector(self):
        data = '''
        module foo(
            int [2:1] bar
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'bar', 'type': 'int', 'dir': 'in', 'dimensions': [['2','1']]};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_input_typed_scalar(self):
        data = '''
        module foo(
            input logic a
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'a', 'type': 'logic', 'dir': 'in'};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_input_untyped_scalar(self):
        data = '''
        module foo(
            input a
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'a', 'type': None, 'dir': 'in'};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_input_typed_vector_downto(self):
        data = '''
        module foo(
            input logic[7:0] a
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'a', 'type': 'logic', 'dir': 'in', 'dimensions': [['7','0']]};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_input_typed_vector_to(self):
        data = '''
        module foo(
            input logic[0:1] a
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'a', 'type': 'logic', 'dir': 'in', 'dimensions': [['0','1']]};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_input_typed_vector_2dim(self):
        data = '''
        module foo(
            input logic[7:0][1:3] a
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'a', 'type': 'logic', 'dir': 'in', 'dimensions': [['7','0'],['1','3']]};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_input_typed_vector_3dim(self):
        data = '''
        module foo(
            input logic[7:0][2:2][1:3] a
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'a', 'type': 'logic', 'dir': 'in', 'dimensions': [['7','0'],['2','2'],['1','3']]};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_input_typed_vector_parameterized(self):
        data = '''
        module foo #(
            parameter int WIDTH
        ) (
            input logic[WIDTH-1:0] a_b_c
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'a_b_c', 'type': 'logic', 'dir': 'in', 'dimensions': [['WIDTH-1','0']]};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_output_typed_scalar(self):
        data = '''
        module foo(
            output logic o
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'o', 'type': 'logic', 'dir': 'out'};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_output_untyped_scalar(self):
        data = '''
        module foo(
            output o1
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'o1', 'type': None, 'dir': 'out'};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_output_typed_vector_downto(self):
        data = '''
        module foo(
            output byte[7:0] a
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'a', 'type': 'byte', 'dir': 'out', 'dimensions': [['7','0']]};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_inout_typed_scalar(self):
        data = '''
        module foo(
            inout logic io
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'io', 'type': 'logic', 'dir': 'inout'};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_inout_untyped_scalar(self):
        data = '''
        module foo(
            inout IO
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 'IO', 'type': None, 'dir': 'inout'};
        self.assertEqual( ports[0].toDict(), exp );

    def test_single_inout_typed_vector_downto(self):
        data = '''
        module foo(
            inout string[7:0] s
        );
        endmodule
        '''

        cst = self.parse_verilog(data);
        module = cst.tree.find({"tag": "kModuleDeclaration"});
        ports = get_ports(module);

        self.assertEqual( len(ports), 1 );

        exp = {'name': 's', 'type': 'string', 'dir': 'inout', 'dimensions': [['7','0']]};
        self.assertEqual( ports[0].toDict(), exp );

