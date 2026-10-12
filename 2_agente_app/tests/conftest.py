"""
Fixtures compartilhadas para os testes do agente
"""

import sys
from pathlib import Path

# Garante que o modulo shared esta no path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Garante que os modulos do proprio agente (domain, ports, adapters, graph) estao no path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
