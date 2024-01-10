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

    def test_single_input(self):
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

        self.assertTrue( False ); #TODO test port attributes


