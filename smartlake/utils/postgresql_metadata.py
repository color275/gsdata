import psycopg2

def get_postgresql_table_metadata(database, table_name):
    connection_string = f"host={database.host} port={database.port} dbname={database.sid} user={database.username} password={database.password}"
    conn = psycopg2.connect(connection_string)

    cursor = conn.cursor()

    try:
        # 테이블 존재 여부 확인
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema||'.'||table_name = LOWER('{table_name}')
        """)
        table_exists = cursor.fetchone()[0]

        if table_exists == 0:
            raise ValueError(f"테이블 '{table_name}'이(가) 데이터베이스에 존재하지 않습니다.")

        # 테이블 코멘트 가져오기
        cursor.execute(f"""
            SELECT obj_description(('"'||table_schema||'"."'||table_name||'"')::regclass, 'pg_class')
            FROM information_schema.tables
            WHERE table_schema||'.'||table_name = LOWER('{table_name}')
        """)
        table_comment = cursor.fetchone()
        table_comment = table_comment[0] if table_comment else f'{table_name}의 메타데이터'

        # 컬럼 메타데이터 가져오기
        cursor.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema||'.'||table_name = LOWER('{table_name}')
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()

        # 컬럼 코멘트 가져오기
        cursor.execute(f"""
            SELECT column_name, col_description(('"'||table_schema||'"."'||table_name||'"')::regclass, ordinal_position)
            FROM information_schema.columns
            WHERE table_schema||'.'||table_name = LOWER('{table_name}')
        """)
        column_comments = {row[0]: row[1] for row in cursor.fetchall()}

        # Primary Key 정보 가져오기
        cursor.execute(f"""
            SELECT a.attname AS column_name
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            JOIN pg_class c ON c.oid = i.indrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE i.indisprimary
            AND n.nspname || '.' || c.relname = LOWER('{table_name}')
        """)
        primary_keys = [row[0] for row in cursor.fetchall()]

        return {
            'table_comment': table_comment,
            'columns': columns,
            'column_comments': column_comments,
            'primary_keys': primary_keys
        }

    finally:
        cursor.close()
        conn.close()