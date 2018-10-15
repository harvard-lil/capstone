This directory collects scripts that apply updates to our data.

Scripts in this directory can be run by `fab run_edit_script:script_name`

Well-behaved edit scripts should:

* Have a `make_edits(dry_run=True)` function that does the work. The function can also accept other keyword arguments.
* Not write to the database unless explicitly passed `dry_run=False`.
* Run blocks of work in transactions. An edit script should not commit a transaction until it is safe to do so, meaning
    it is safe to kill the script at any time and restart it. If you aren't sure, just run the entire function in a
    transaction.