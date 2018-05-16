CREATE OR REPLACE FUNCTION denormalize_source() RETURNS trigger AS
$$

  /*
    This function updates tables with source fields for denormalized data. Example use:

      CREATE TRIGGER denormalize_source
          BEFORE UPDATE
          ON capdb_jurisdiction FOR EACH ROW
          EXECUTE PROCEDURE denormalize_source('capdb_casemetadata', 'jurisdiction_id', 'id', '{"slug": "jurisdiction_slug"}');

  */

  // each set of four arguments is a destination table for denormalization.
  for(var i=0;i<TG_ARGV.length;i+=4) {

    // load ARGV values
    dest_table = TG_ARGV[i];
    dest_id_column = TG_ARGV[i+1];
    source_id_column = TG_ARGV[i+2];
    var field_map = JSON.parse(TG_ARGV[i+3]);
    var source_columns = Object.keys(field_map);

    // find changed values
    var dest_columns = [];
    var dest_values = [];
    var index = 0;
    source_columns.forEach(function(source_column){
      if(NEW[source_column] !== OLD[source_column]){
        index += 1;
        dest_columns.push(field_map[source_column] + '=$' + index);
        dest_values.push(NEW[source_column]);
      }
    });

    // if no changed values, we're done
    if (!index)
      continue;

    // add ID to placeholder values
    dest_values.push(NEW[source_id_column]);

    // update destination fields
    var sql = 'UPDATE ' + dest_table + ' SET ' + dest_columns.join(', ') + ' WHERE ' + dest_id_column + '=$' + (index+1);
    plv8.elog(WARNING, sql, JSON.stringify(dest_values));
    plv8.execute(sql, dest_values);
  }

$$
LANGUAGE "plv8";