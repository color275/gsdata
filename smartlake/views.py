from rest_framework import viewsets
from rest_framework.response import Response
from .models import Tables, Databases
from .serializers import *
from rest_framework.views import APIView
from django.db import connection
from django.http import JsonResponse

def load_databases(request):
    db_env_id = request.GET.get('db_env')
    databases = Databases.objects.filter(id_dbenv=db_env_id).values('id', 'db_name')
    return JsonResponse(list(databases), safe=False)


class GetTableInfoByIntervalView(APIView):
    def get(self, request, *args, **kwargs):
        interval_type = request.query_params.get('interval_type', "None")
        load_type = request.query_params.get('load_type', "None")
        db_env = request.query_params.get('db_env', "None")
        db_name = request.query_params.get('db_name', "None")
        use_yn = request.query_params.get('use_yn', "None")

        if interval_type == "None":
            return Response({"error": "interval_type is required"}, status=400)
        
        with connection.cursor() as cursor:
            # 1. Í∏∞Î≥∏ ?Öå?ù¥Î∏? ?†ïÎ≥? Ï°∞Ìöå
            cursor.execute(f"""
                SELECT 
                p.project_cd,
                t.id AS table_id,
                d.db_name, 
                dt.db_type_name AS db_type,
                d.host,
                d.port,
                d.options,
                t.table_name, 
                t.sql_where,
                li.interval_type,
                lm.load_type,
                e.db_env_name AS env_name,                
                pt.partition_type,
                t.catalog_db_name,
                t.catalog_table_name,
                t.spark_num_executors,
                t.spark_executor_cores,
                CONCAT(t.spark_executor_memory, 'g') AS spark_executor_memory,
                t.spark_partitionColumn,
                t.spark_lowerBound,
                t.spark_upperBound,
                t.spark_numpartitions,
                t.spark_fetchsize,
                t.spark_query,
                t.cdc_yn,
                t.use_yn,
                d.backup_bucket,
                d.iceberg_bucket
            FROM 
                sl_databases d
            JOIN 
                sl_database_types dt ON d.id_databasetype = dt.id
            JOIN 
                sl_tables t ON d.id = t.id_db
            JOIN 
                sl_load_interval li ON li.id = t.id_load_interval
            JOIN 
                sl_load_method lm ON lm.id = t.id_load_method
            JOIN 
                sl_db_env e ON d.id_dbenv = e.id
            JOIN 
                sl_project p ON p.id = d.id_project
            LEFT OUTER JOIN 
                sl_partition_type pt ON pt.id = t.id_partition_type
            WHERE 
                ('{interval_type}' = 'None' OR li.interval_type = '{interval_type}')
                AND ('{load_type}' = 'None' OR lm.load_type = '{load_type}')
                AND ('{db_env}' = 'None' OR e.db_env_name = '{db_env}')
                AND ('{db_name}' = 'None' OR d.db_name = '{db_name}')
                AND ('{use_yn}' = 'None' OR t.use_yn = '{use_yn}')                 
            """)

            



            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            result = [dict(zip(columns, row)) for row in rows]

            # 2. Í∞? ?Öå?ù¥Î∏îÏùò Ïª¨Îüº ?†ïÎ≥?, Primary Key, Partition Ïª¨Îüº ?†ïÎ≥¥Î?? Ï°∞Ìöå?ïò?ó¨ Ï°∞Î¶Ω
            for row in result:
                table_id = row['table_id']  # ?Öå?ù¥Î∏? ID ?Ç¨?ö©

                # 2.1 Ïª¨Îüº ?†ïÎ≥? Ï°∞Ìöå
                cursor.execute("""
                    SELECT column_name
                    FROM sl_columns
                    WHERE id_table = %s
                    AND use_yn = 'Y'
                """, [table_id])
                row['columns'] = [col[0] for col in cursor.fetchall()]

                # 2.2 Primary Key Ïª¨Îüº ?†ïÎ≥? Ï°∞Ìöå
                cursor.execute("""
                    SELECT column_name
                    FROM sl_columns
                    WHERE id_table = %s
                    AND pk_yn = 'Y'
                """, [table_id])
                row['primary_keys'] = [col[0] for col in cursor.fetchall()]

                # 2.3 Partition Ïª¨Îüº ?†ïÎ≥? Ï°∞Ìöå
                cursor.execute("""
                    SELECT column_name
                    FROM sl_columns
                    WHERE id_table = %s
                    AND partition_yn = 'Y'
                """, [table_id])
                row['partition_columns'] = [col[0] for col in cursor.fetchall()]

        return Response(result)
    
# class TablesViewSet(viewsets.ModelViewSet):
#     serializer_class = TablesSerializer

#     def get_queryset(self):
#         table_name = self.request.query_params.get('table_name', None)
#         if table_name is not None:
#             return Tables.objects.filter(table_name=table_name)
#         return Tables.objects.all()
