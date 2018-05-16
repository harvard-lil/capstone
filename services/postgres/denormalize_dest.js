CREATE OR REPLACE FUNCTION denormalize_dest() RETURNS trigger AS
$$

  /*
    This function updates tables with destination fields for denormalized data. Example use:

      CREATE TRIGGER denormalize_dest
          BEFORE INSERT OR UPDATE
          ON capdb_casemetadata FOR EACH ROW
          EXECUTE PROCEDURE denormalize_dest('capdb_jurisdiction', 'jurisdiction_id', 'id', '{"slug": "jurisdiction_slug"}');

     Whenever capdb_casemetadata.jurisdiction_id is changed, values will be copied from capdb_jurisdiction.slug to
     capdb_casemetadata.jurisdiction_slug based on jurisdiction_id = capdb_jurisdiction.id.
  */

  // each set of four arguments is a source field for denormalization.
  for(var i=0;i<TG_ARGV.length;i+=4) {

    // bail out if there is no new foreign key from which to copy values
    foreign_key = TG_ARGV[i+1];
    if (
        (TG_OP === "UPDATE" && NEW[foreign_key] === OLD[foreign_key]) ||
        (TG_OP === "INSERT" && !NEW[foreign_key])
    ){
      continue;
    }

    // load configuration from arguments
    var source_table = TG_ARGV[i];
    var source_id_column = TG_ARGV[i+2];
    var field_map = JSON.parse(TG_ARGV[i+3]);
    var source_columns = Object.keys(field_map);

    // if foreign key has been nulled, set destination fields to null
    if(!NEW[foreign_key]){
      source_columns.forEach(function(source_column){
        NEW[field_map[source_column]] = null;
      });

    // if foreign key not nulled, fetch source fields and copy to destination fields
    }else {
      var rows = plv8.execute('SELECT ' + source_columns.join(', ') + ' FROM ' + source_table + ' WHERE ' + source_id_column + ' = $1', [NEW[foreign_key]]);

      // a valid foreign key should always return exactly one result
      if(rows.length !== 1)
        continue;

      // copy each value
      var row = rows[0];
      Object.keys(row).forEach(function (source_column) {
        NEW[field_map[source_column]] = row[source_column];
      });

    }
  }

  return NEW;

$$
LANGUAGE "plv8";