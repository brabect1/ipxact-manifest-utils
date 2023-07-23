IP-XACT
=======

Resources
---------

* XML Schemas

  * Official Accellera schemas: http://www.spiritconsortium.org/XMLSchema/
  * Schema copies on github: https://github.com/edaa-org/IPXACT-Schema
  
* Examples

  * Simple catalog file https://gist.github.com/berndca/8a9a95eb6a20a9b07e2c9a44045ec810
  * kactus2 example library https://github.com/kactus2/ipxactexamplelib
  * legacy SPIRIT bus definitions http://www.accellera.org/busdefs
  * LEON2 example https://www.accellera.org/images/activities/committees/ip-xact/Leon2_1685-2014.zip
  * kactus2 pulpino example https://github.com/kactus2/pulpinoexperiment
  * Xilinx IPs: Note that Xilinx has settled on 1685-2009, which is structurally different than newer standards.
    * Vivado-distributed IPs under ``data/ip/xilinx/<ip>/``
    * rgb2dvi IP: https://github.com/Digilent/vivado-library/blob/master/ip/rgb2dvi/component.xml
    * pynq pattern controller IP: https://github.com/Xilinx/PYNQ/blob/master/boards/ip/pattern_controller_1.1/component.xml

* tools

  * ipyxact https://github.com/olofk/ipyxact
  
    * https://github.com/olofk/ipxact_gen
    
  * generator of Xilinx-compatible ``component.xml`` https://github.com/Nic30/ipCorePackager
  
* Misc

  * ARM IP-XACT Components Reference Manual https://developer.arm.com/documentation/ddi0429/a
  * note on ``ipx::` Tcl namespace in Xilinx Vivado https://support.xilinx.com/s/question/0D52E00006iHkr7SAC/custom-ipxact-specification-for-system-generator-blocks?language=en_US

Components
----------

* ``model``

  * ``instantiations``
  
    * ``componentInstantiation`` (s): Collects information needed to instantiate a component model.
    
      * ``name``: Instantiation ID.
      * (opt.) ``moduleName``: Can be used identify (top) module represented by the instantiation/model.
      * (opt.) ``moduleParameters``: Enumerates module parameters. Can be used if the instantiation/model
        represents a parameterized HDL model.

        .. todo:: How does it relate or differ from other parameter elements? There is no clear
           difference betweem ``component.model.instantiations.componentInstantiation.moduleParameters``
           and ``component.model.instantiations.componentInstantiation.parameters`` except that the
           former is more pertinent to HDL models (as IEEE Std. gives examples of various representations
           in different HDLs).
        
      * (opt.) ``fileSetRef`` (s): Reference to a fileSet in the same IP-XACT document.
      * (opt.) ``parameters``: Describes additional parameters for the enclosing instantiation element.
      * (opt.) ``vendorExtensions``

* ``fileSets``

  * ``fileSet`` (s):
  
    * ``name``: fileSet's ID.
    * ``file`` (s): Describes a file/directory within a fileSet.
    
      * ``name``: A file path. The value is of ``ipxact:stringURIExpression`` type.
      * ``fileType`` (s): Identifies the file type. Can be one of the Std.-defined types (e.g. ``verilogSource``, see C.8 in 1685-2014; 1685-2022 defines more pre-defined types) or ``user``. For custom types use:
``<ipxact:fileType user="...">user</ipxact:fileType>``.

        There can be more fileTypes for a file. For example Xilinx uses the user fileType element to describe
        various xilinx-specific use cases of the file::
        
            <!-- IEEE std. 1685-2009 -->
            <spirit:file>
                <spirit:name>src/rgb2dvi.xdc</spirit:name>
                <spirit:userFileType>xdc</spirit:userFileType>
                <spirit:userFileType>IMPORTED_FILE</spirit:userFileType>
                <spirit:userFileType>USED_IN_implementation</spirit:userFileType>
                <spirit:userFileType>USED_IN_synthesis</spirit:userFileType>
            </spirit:file>


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
