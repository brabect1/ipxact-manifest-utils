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
import anytree
import verible_verilog_syntax

class Port(object):
    pass

def get_ports(module_data: verible_verilog_syntax.SyntaxData):
    ports = [];
    for port in module_data.iter_find_all({"tag": ["kPortDeclaration", "kPort"]}):
        ports.append( port.find({"tag": ["SymbolIdentifier", "EscapedIdentifier"]}).text );

    return ports;

def process_file_data(path: str, data: verible_verilog_syntax.SyntaxData):
    for module in data.tree.iter_find_all({"tag": "kModuleDeclaration"}):
        name = module.find({"tag": "kModuleHeader"});
        if name:
            name = name.find({"tag": ["SymbolIdentifier", "EscapedIdentifier"]},iter_=anytree.PreOrderIter);
            if name:
                name = name.text;

        if name:
            print(f"[{name}]");

        ports = get_ports(module);
        if ports:
            for port in ports:
                print(f"\t{port}");


parser_path = sys.argv[1];
file_path = sys.argv[2];

parser = verible_verilog_syntax.VeribleVerilogSyntax(executable=parser_path);
file_data = parser.parse_file(file_path);

process_file_data(file_path, file_data);

