# Copyright 2023 Tomas Brabec
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

import sys
from systemrdl import RDLListener, RDLWalker
from systemrdl.node import FieldNode, AddressableNode, RegNode

# Define a listener that will print out the register model hierarchy
class rdlWriterListener(RDLListener):
    f = sys.stdout;

    def __init__(self, f=None):
        self.indent = 0
        if f is not None:
            self.f = f;

    def enter_Component(self, node):
        if not isinstance(node, FieldNode):
            s = "\t"*self.indent;
            type_name = None; # node.type_name;
            if type_name is None:
                if isinstance(node, RegNode):
                    type_name = 'reg';
                elif isinstance(node, AddressableNode):
                    type_name = 'addrmap';
                else:
                    type_name = '???';
            s += type_name;
            if self.indent == 0:
                s += ' ' + node.get_path_segment();
            s += ' {';
            self.indent += 1
            print(s, file=self.f)

    def enter_Field(self, node):
        # Print some stuff about the field
        bit_range_str = "[%d:%d]" % (node.high, node.low)
        sw_access_str = "sw=%s" % node.get_property('sw').name
        s = "\t"*self.indent + 'field {' + sw_access_str + ';} ' + node.get_path_segment() + bit_range_str + ';';
        print(s, file=self.f)

    def exit_Component(self, node):
        if not isinstance(node, FieldNode):
            self.indent -= 1
            s = "\t"*self.indent + '}';
            if self.indent > 0:
                s += ' ' + node.get_path_segment();
                if isinstance(node, RegNode):
                    s += ' @0x{:x}'.format( node.address_offset );
            s += ';'
            print(s, file=self.f)
