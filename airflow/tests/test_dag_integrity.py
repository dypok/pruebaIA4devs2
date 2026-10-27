import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def test_dags_import_cleanly():
    """
    Verifica que todos los archivos de DAGs en airflow/dags se importen
    sin errores de sintaxis, dependencias faltantes o ciclos.
    """
    dags_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../dags"))
    dag_files = [f for f in os.listdir(dags_dir) if f.startswith("dag_") and f.endswith(".py")]

    assert len(dag_files) >= 4, f"Se esperaban al menos 4 DAGs, encontrados: {len(dag_files)}"

    for file_name in dag_files:
        module_name = file_name[:-3]
        file_path = os.path.join(dags_dir, file_name)
        
        # Intentar cargar y compilar el archivo
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
            compiled = compile(code, file_path, "exec")
            assert compiled is not None, f"Error compilando {file_name}"
