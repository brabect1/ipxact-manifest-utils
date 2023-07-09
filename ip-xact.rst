IP-XACT
=======

Resources
---------

* Examples

  * Simple catalog file https://gist.github.com/berndca/8a9a95eb6a20a9b07e2c9a44045ec810
  * kactus2 example library https://github.com/kactus2/ipxactexamplelib
  * legacy SPIRIT bus definitions http://www.accellera.org/busdefs
  * LEON2 example https://www.accellera.org/images/activities/committees/ip-xact/Leon2_1685-2014.zip
  * kactus2 pulpino example https://github.com/kactus2/pulpinoexperiment

* tools

  * ipyxact https://github.com/olofk/ipyxact
  
    * https://github.com/olofk/ipxact_gen
    
  * generator of Xilinx-compatible ``component.xml`` https://github.com/Nic30/ipCorePackager
  
* Misc

  * ARM IP-XACT Components Reference Manual https://developer.arm.com/documentation/ddi0429/a
  * note on ``ipx::` Tcl namespace in Xilinx Vivado https://support.xilinx.com/s/question/0D52E00006iHkr7SAC/custom-ipxact-specification-for-system-generator-blocks?language=en_US
  
ipyxact
-------

printing IpxactItem::

    from ipyxact.ipyxact import Component, Catalog
    
    # https://stackoverflow.com/a/65808327
    def _xml_pretty_print(current, parent=None, index=-1, depth=0):
        for i, node in enumerate(current):
            _xml_pretty_print(node, current, i, depth + 1)
        if parent is not None:
            if index == 0:
                parent.text = '\n' + ('\t' * depth)
            else:
                parent[index - 1].tail = '\n' + ('\t' * depth)
            if index == len(parent) - 1:
                current.tail = '\n' + ('\t' * (depth - 1))
    
    if __name__ == "__main__":
        catalog = Catalog();
        catalog.load(io.StringIO(data['kactus2-spi_example']));
        root = ET.Element('' + catalog._tag)
        catalog._write(root, '')
    
        #---->>>>
        # in python 3.9+: tree = ET.ElementTree(root)
        # in python 3.9+: ET.indent(tree, space="\t", level=0)
        _xml_pretty_print(root)
        #<<<<----
        s = ET.tostring(root, encoding="unicode")
        sys.stdout.write(s);

create an IP-XACT element manually::

    import ipyxact.ipyxact
    
    if __name__ == "__main__":
        catalog = ipyxact.ipyxact.Catalog();
        #catalog.load(io.StringIO(data['kactus2-spi_example']));
        
        catalogs = ipyxact.ipyxact.Catalogs();
        catalog.catalogs = catalogs;
        
        vlnv = ipyxact.ipyxact.Vlnv();
        vlnv.vendor = 'my_vendor'
        vlnv.version = '1.1'
        vlnv.name = 'my_name'
        vlnv.library = 'my_lib'
        
        ipxactFile = ipyxact.ipyxact.IpxactFile();
        ipxactFile.name = '../some/path'
        ipxactFile.vlnv = vlnv
        
        catalogs.ipxactFile.append( ipxactFile );
        
        catalog.write(sys.stdout,indent='  ')
