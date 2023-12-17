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
    * clk mux: https://github.com/Xilinx/IIoT-EDDP/blob/master/SDSoC/platforms/arty_z7_20_foc/hw/vivado/arty_z7_20_foc.ipdefs/ip_repo_0/clk_mux/component.xml

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

  * (opt.) ``instantiations``
  
    * ``componentInstantiation`` (s): Collects information needed to instantiate a component model.
    
      * ``name``: Instantiation ID of ``xs:NMTOKEN`` type (i.e. word chars with ``:``, ``-`` and ``_``).
      * (opt.) ``language``: Specifies the HDL used for a specific instantiation [IEEE Std. 1685-2014].
        However, there seems to be no restriction on the actual value and hence may be used to indicate
        whatever "language" is relevant to the ``fileSetRef(s)`` in the enclosing instantiation.
      
      * (opt.) ``moduleName``: Can be used identify (top) module represented by the instantiation/model.
      * (opt.) ``moduleParameters``: Enumerates module parameters. Can be used if the instantiation/model
        represents a parameterized HDL model.

        .. todo:: How does it relate or differ from other parameter elements? There is no clear
           difference betweem ``component.model.instantiations.componentInstantiation.moduleParameters``
           and ``component.model.instantiations.componentInstantiation.parameters`` except that the
           former is more pertinent to HDL models (as IEEE Std. gives examples of various representations
           in different HDLs).
        
      * (opt.) ``fileSetRef`` (s): Reference to a fileSet in the containing document (i.e. the same IP-XACT document) or another document referenced by VLNV.
      
        The fact that there can be multiple ``fileSetRef`` elements in the instantiation
        and that they can point to an arbitrary IP-XACT document could be used to capture
        dependencies. One inconvenience is that it the dependency would better be captured
        at the instantiation/model level rather than pointing to a file set. If using this
        mechanism for capturing dependencies, a well-defined file set naming convention
        would likely be inevitable.
        
        Xilinx seems to use similar approach except that it puts the dependency information
        into a ``fileSet.vendorExtension``. See https://github.com/Xilinx/revCtrl/blob/master/ip/axi_iic_0/axi_iic_0.xml
        and search for ``xilinx_vhdlbehavioralsimulation_xilinx_com_ip_blk_mem_gen_8_2__ref_view_fileset``.
        
      * (opt.) ``parameters``: Describes additional parameters for the enclosing instantiation element.
      * (opt.) ``vendorExtensions``
      
  * (opt.) ``ports``
  
    * ``port`` (s)
  
  * (opt.) ``views``
  
    .. note:: The only thing that a ``view`` element does is referring to a particular instantiation
       and optionally binding it to a set of tools/environments. If the tool binding information
       is irrelevant for the IP-XACT recipient, it seems that processing the ``views`` sub-tree can
       be avoided.
  
    * ``view`` (s)
    
      * ``name``
      * (opt.) ``componentInstantiationRef``
      * (opt.) ``envIdentifier`` (s): This elements can specify tool/environment for which the enclosing
        view applies. For example, it may specify a synthesis tool or a simulation tool to be used for
        a particular view.

* ``fileSets``

  * ``fileSet`` (s):
  
    * ``name``: fileSet's ID.
    * (opt.) ``displayName``
    * (opt.) ``description``
    * (opt.) ``group``: A single, descriptive word identifying the enclosing file sets' purpose.
    * ``file`` (s): Describes a file/directory within a file set.
    
      .. note:: ``file`` XML element can have any XML attributes. Hence vendors may
         use whatever custom attributes they like. Obviously, anything custom here
         is non-standard and rises chances for attribute name conlisions and misinterpretation.
    
      * ``name``: A file path. The value is of ``ipxact:stringURIExpression`` type.
      * ``fileType`` (s): Identifies the file type. Can be one of the Std.-defined types (e.g. ``verilogSource``, see C.8 in 1685-2014; 1685-2022 defines more pre-defined types) or ``user``. For custom types use: ``<ipxact:fileType user="...">user</ipxact:fileType>``.

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

      * (opt.) ``vendorExtensions``: ``file`` can have vendor extensions.
      
    * (opt.) ``vendorExtensions``: ``fileSet`` can have vendor extensions.

Perameterized Ports
-------------------

Many reusable IPs come with parameters and parameterized ports. See a GPIO controller IP (VHDL, https://github.com/tudortimi/ipxact/tree/master/tests/Leon2/xml/spiritconsortium.org/Leon2RTL/gpio/1.2)::

    entity gpio is
    generic (
          GPI_BITS : integer := 8;
          ...
          );
    
    port (
          gpi:        in     std_logic_vector(GPI_BITS-1 downto 0);
          ...
          );
    end gpio;

Corresponding IP-XACT 2014 would look like follows::

    <ipxact:component ...>
       ...
       <ipxact:model>
          ...
          <ipxact:instantiations>
             <ipxact:componentInstantiation>
                <ipxact:name>vhdlsource</ipxact:name>
                <ipxact:language>vhdl</ipxact:language>
                <ipxact:moduleName>gpio(rtl)</ipxact:moduleName>
                <ipxact:moduleParameters>
                   <ipxact:moduleParameter minimum="1" maximum="32" dataType="integer">
                      <ipxact:name>GPI_BITS</ipxact:name>
                      <ipxact:value>gpi</ipxact:value>            <!-- Notice the use of `gpi` as value variable/ID -->
                   </ipxact:moduleParameter>
                   ...
                </ipxact:moduleParameters>
             </ipxact:componentInstantiation>
          </ipxact:instantiations>
          <ipxact:ports>
             <ipxact:port>
                <ipxact:name>gpi</ipxact:name>
                <ipxact:wire>
                   <ipxact:direction>in</ipxact:direction>
                   <ipxact:vectors>
                      <ipxact:vector>
                         <ipxact:left>gpi - 1</ipxact:left>
                         <ipxact:right>0</ipxact:right>           <!-- Notice the use of `gpi` as value variable/ID -->
                      </ipxact:vector>
                   </ipxact:vectors>
                </ipxact:wire>
             </ipxact:port>
             ...
          </ipxact:ports>
          ...
       </ipxact:model>
       ...
       <ipxact:parameters>
          <ipxact:parameter parameterId="gpi" resolve="user" order="0" configGroups="requiredConfig"
                            prompt="Number of input:"
                            minimum="1"
                            maximum="32">
             <ipxact:name>GPI_BITS</ipxact:name>
             <ipxact:value>8</ipxact:value>
          </ipxact:parameter>
          ...
       </ipxact:parameters>
    </ipxact:component>

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
