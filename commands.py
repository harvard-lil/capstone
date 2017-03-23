import click
from process_ingested_xml import fill_case_page_join_table
from set_up_postgres import update_postgres_env


@click.group()
def cli():
    pass

def add_command(func):
    cli.add_command(click.command()(func))

add_command(fill_case_page_join_table)
add_command(update_postgres_env)

if __name__ == '__main__':
    cli()