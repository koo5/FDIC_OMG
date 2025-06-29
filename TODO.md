Let us review the design . 

# The python conversion command should be named csv2rdf and has these tasks:

 * load given annotations file (annotations/fdic_banks.ttl by default) with a proper rdf parser (rdflib) into a rdflib graph.
 * read the header of the CSV file and assert column descriptions into the graph.
 * link the columns to the annotations.
 * dump the resulting graph into <output_directory>/table.ttl
 * dump the resulting graph into <output_directory>/full.ttl
 * parse the CSV file rows:
 * * appending RDF descriptions of the rows to <output_directory>/full.ttl 
 * * appending RDF descriptions of the rows to <output_directory>/<chunk_name>.ttl
 * <output_directory>/full.ttl will be kept for third-party applications.
 * <output_directory>/full.ttl and chunks will be listed in <output_directory>/table_manifest.json
 * generate a rdftab instance that will take an URL query parameter to display a table view given the manifest.

We should make sure to use rdflib parsers and serializers for all RDF operations except the streamed output of the CSV rows, which will be done with a custom serializer that writes triples directly to the output file.

# The command annotations_yaml_to_ttl should:

 * load the given annotations YAML file (annotations/fdic_banks.yaml by default)
 * convert it to a rdflib graph
 * dump the graph (into annotations/fdic_banks.ttl by default)

# The command annotations_ttl_to_yaml should:

 * load the given annotations TTL file (annotations/fdic_banks.ttl by default)
 * convert it to a YAML file
 * dump the YAML file (into annotations/fdic_banks.yaml by default)


# rdftab:
 * should have a concept of sources.
 * * /api/rdftab and /sparql would be sources which always query the respective backends.
 * * the loaded table.ttl and chunks files obtained from the manifest should constitute another source, one that queries the loaded table.ttl and the currently loaded chunk (controlled by pagination).
 * when constructing a node or a list of quads, rdftab should use all sources to construct the result.
