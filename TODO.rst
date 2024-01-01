- create a regular github repository

  - start adding unit tests

- vlog2ipxact

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

  - add conversion to et
  - put <memMaps> to correct place in element order

