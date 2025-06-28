Let us review the design . The python conversion script has these tasks:

1) load annotations/fdic_banks.ttl with a proper rdf parser (rdflib) into a rdflib graph.
2) read the header of the CSV file and assert column descriptions into the graph.
3) link the columns to the annotations.
4) dump the resulting graph into <output_directory>/table.ttl

* Produce the single file RDF output
** Produce the RDF that describes the CSV
**

produce the RDF that describes the CSV .