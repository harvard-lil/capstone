A citation graph showing the connections between CAP cases. 

About citation graphs
---------------------

A *graph* is a collection of nodes and edges (connections between nodes). In a *citation graph*, nodes are cases and edges are citations from one case to another. You can use the citation graph to answer questions like "what is the most influential case?", "what jurisdictions cite most often to this jurisdiction?", and "what clusters is this case a part of?"
 
Graph format
------------

We offer the citation graph in the form of a zipped CSV file. The CSV is an "[adjacency list](https://en.wikipedia.org/wiki/Adjacency_list)" showing case ids and the case ids they cite to, in the format:

```
source_id, dest_id, dest_id ...
source_id, dest_id, dest_id ...
```

Limitations
-----------

The graph contains only unambiguous edges; it does not include citations that we were unable to match to a case, or citations that matched to more than one case.

The graph does not include case metadata; if you need metadata you will need to link case IDs to metadata from bulk export files. We may in the future offer metadata through another format such as GraphML.
