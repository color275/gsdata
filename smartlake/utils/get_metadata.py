from ..models import Databases, Tables, Columns
from .oracle_metadata import get_oracle_table_metadata
from .postgresql_metadata import get_postgresql_table_metadata

def get_or_create_table_metadata(db_id: int, table_id: int, table_name: str):
    try:
        database = Databases.objects.get(id=db_id)
    except Databases.DoesNotExist:
        raise ValueError(f"'{database}'에 해당하는 데이터베이스가 존재하지 않습니다.")

    table_instance = Tables.objects.filter(id=table_id).first()
    
    if table_instance and Columns.objects.filter(id_table=table_instance).exists():
        raise ValueError(f"테이블 '{table_name}'에 컬럼 정보가 이미 존재합니다.")

    if database.id_databasetype.db_type_name == 'Oracle':
        metadata = get_oracle_table_metadata(database, table_name)
    elif database.id_databasetype.db_type_name == 'PostgreSQL':
        metadata = get_postgresql_table_metadata(database, table_name)
    else:
        raise ValueError(f"지원되지 않는 데이터베이스 유형입니다: {database.id_databasetype.db_type_name}")

    table_instance, created = Tables.objects.get_or_create(
        # table_name=table_name.lower(),
        id=table_id,
        id_db=database,
    )

    for column in metadata['columns']:
        column_name, data_type, nullable = column
        is_pk = 'Y' if column_name in metadata['primary_keys'] else 'N'
        column_comment = metadata['column_comments'].get(column_name, f'{column_name} 컬럼')

        Columns.objects.get_or_create(
            id_table=table_instance,
            column_name=column_name.lower(),
            defaults={
                'pk_yn': is_pk,
                'partition_yn': 'N',
                'datatype': data_type.lower(),
                'comments': column_comment,
            }
        )