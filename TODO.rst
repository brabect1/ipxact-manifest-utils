- create a regular github repository

  - start adding unit tests

- vlog2ipxact

  - do not add ``<moduleParameters>`` if there are none (XML validation would fail otherwise)

  - fix output port in Verilog

    example (problem with ``q`` recognized as ``in``, other potential problem is port type; root
    cause is the Verilog-style ports are defined as ``kPortReference`` and hence need to find the
    referenced port and type declaration(s))::

        module foo(a,b,q);
        input a, b;
        output q;
        wire a, b;
        wire q;
        endmodule

- rdl2ipxact

  - test existing ``<memoryMap>``

