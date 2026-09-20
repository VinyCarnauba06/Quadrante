import os
import sys

caminho_projeto: str = os.path.join(os.path.dirname(__file__), "quadrante-python")
if caminho_projeto not in sys.path:
    sys.path.insert(0, caminho_projeto)

os.chdir(caminho_projeto)
from test import executar_benchmarks

if __name__ == "__main__":
    sys.exit(executar_benchmarks())
