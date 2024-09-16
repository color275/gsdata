import cx_Oracle

def get_oracle_table_metadata(database, table_name):
    connection_string = f"{database.username}/{database.password}@{database.host}:{database.port}/{database.sid}"
    conn = cx_Oracle.connect(connection_string)

    cursor = conn.cursor()
    
    try:
        # 테이블 존재 여부 확인
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM all_tables
            WHERE owner||'.'||table_name = UPPER('{table_name}')
        """)
        table_exists = cursor.fetchone()[0]

        if table_exists == 0:
            raise ValueError(f"테이블 '{table_name}'이(가) 데이터베이스에 존재하지 않습니다.")

        # 테이블 코멘트 가져오기
        cursor.execute(f"""
            SELECT comments
            FROM all_tab_comments
            WHERE owner||'.'||table_name = UPPER('{table_name}')
        """)
        table_comment = cursor.fetchone()
        table_comment = table_comment[0] if table_comment else f'{table_name}의 메타데이터'

        # 컬럼 메타데이터 가져오기
        cursor.execute(f"""
            SELECT column_name, data_type, nullable
            FROM all_tab_columns
            WHERE owner||'.'||table_name = UPPER('{table_name}')
            ORDER BY column_id
        """)
        columns = cursor.fetchall()

        # 컬럼 코멘트 가져오기
        cursor.execute(f"""
            SELECT column_name, comments
            FROM all_col_comments
            WHERE owner||'.'||table_name = UPPER('{table_name}')
        """)
        column_comments = {row[0]: row[1] for row in cursor.fetchall()}

        # Primary Key 정보 가져오기
        cursor.execute(f"""
            SELECT cols.column_name
            FROM all_constraints cons, all_cons_columns cols
            WHERE cons.constraint_type = 'P'
            AND cons.constraint_name = cols.constraint_name
            AND cons.owner = cols.owner
            AND cols.owner||'.'||cols.table_name = UPPER('{table_name}')
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