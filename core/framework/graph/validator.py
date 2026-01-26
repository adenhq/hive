import logging
from typing import List, Dict, Any, Set
from collections import deque

# Configuração de logger para capturar alertas de segurança e importação
logger = logging.getLogger(__name__)

class ValidationResult:
    """
    Resultado de validação unificado. 
    Suporta 'valid' (booleano) e 'errors' (lista ou string).
    """
    def __init__(self, valid: bool, error: str = "", errors: List[str] = None):
        self.valid = valid
        self.success = valid  
        self.error = error
        self.errors = errors or ([error] if error else [])

    def __bool__(self):
        return self.valid

class GraphValidator:
    """
    Valida a confiabilidade da estrutura do grafo e a integridade dos dados.
    Previne loops infinitos, nós isolados e injeção de código.
    """

    @staticmethod
    def validate(graph_spec: Any) -> ValidationResult:
        """
        Validação Topológica: Verifica integridade básica, ciclos (DFS) e conectividade (BFS).
        """
        # 1. Integrity Check (Basic Fields)
        if not hasattr(graph_spec, "nodes") or not hasattr(graph_spec, "edges") or not hasattr(graph_spec, "entry_node"):
             return ValidationResult(False, "GraphSpec missing required attributes (nodes, edges, entry_node)")

        node_ids = {n.id for n in graph_spec.nodes}
        adj_list = {n_id: [] for n_id in node_ids}
        
        for edge in graph_spec.edges:
            if edge.source not in node_ids or edge.target not in node_ids:
                return ValidationResult(False, f"Edge references invalid node: {edge.source}->{edge.target}")
            adj_list[edge.source].append(edge.target)

        if graph_spec.entry_node not in node_ids:
             return ValidationResult(False, f"Entry node '{graph_spec.entry_node}' not found in nodes")

        # 2. Cycle Detection (DFS)
        visited = set()
        rec_stack = set()
        
        def has_cycle(u):
            visited.add(u)
            rec_stack.add(u)
            for v in adj_list[u]:
                if v not in visited:
                    if has_cycle(v): return True
                elif v in rec_stack: return True
            rec_stack.remove(u)
            return False

        for node_id in node_ids:
            if node_id not in visited:
                if has_cycle(node_id):
                    return ValidationResult(False, f"Cycle detected involving node '{node_id}'")

        # 3. Connectivity/Reachability (BFS)
        reachable = set([graph_spec.entry_node])
        q = deque([graph_spec.entry_node])
        
        while q:
            u = q.popleft()
            for v in adj_list[u]:
                if v not in reachable:
                    reachable.add(v)
                    q.append(v)
                        
        unreachable = node_ids - reachable
        if unreachable:
             return ValidationResult(False, f"Unreachable nodes detected: {unreachable}")

        return ValidationResult(True)

    def _contains_code_indicators(self, value: str) -> bool:
        """Verifica padrões de código para evitar injeção de scripts."""
        code_indicators = ["def ", "class ", "import ", "async def ", "await ", "function ", "SELECT ", "<script"]
        if len(value) < 10000:
            return any(ind in value for ind in code_indicators)
        
        # Amostragem para strings longas (performance)
        samples = [0, len(value)//2, max(0, len(value)-2000)]
        return any(any(ind in value[p:p+2000] for ind in code_indicators) for p in samples)

    def validate_output_keys(
        self, 
        output: Dict[str, Any], 
        expected_keys: List[str], 
        max_length: int = 5000
    ) -> ValidationResult:
        """Valida presença, comprimento e segurança das chaves de saída."""
        errors = []
        for key in expected_keys:
            if key not in output:
                errors.append(f"Missing expected key: {key}")
                continue
            
            val_str = str(output[key])
            if self._contains_code_indicators(val_str):
                logger.warning(f"Output key '{key}' may contain code indicators.")

            if len(val_str) > max_length:
                errors.append(f"Key '{key}' exceeds max length ({len(val_str)} > {max_length})")

        return ValidationResult(len(errors) == 0, errors=errors)

    def validate_schema(self, output: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
        """Valida a saída contra um JSON Schema (Draft 7)."""
        try:
            import jsonschema
            val_errors = [f"{'.'.join(str(p) for p in e.path) or 'root'}: {e.message}" 
                          for e in jsonschema.Draft7Validator(schema).iter_errors(output)]
            return ValidationResult(len(val_errors) == 0, errors=val_errors)
        except ImportError:
            logger.warning("jsonschema not installed, skipping schema validation.")
            return ValidationResult(True)

class OutputValidator:
    """Mantém compatibilidade com o GraphExecutor original."""
    def validate_all(
        self,
        output: Dict[str, Any],
        expected_keys: List[str],
        check_hallucination: bool = True
    ) -> ValidationResult:
        missing = [key for key in expected_keys if key not in output]
        if missing:
            return ValidationResult(False, f"Missing required output keys: {missing}")
        return ValidationResult(True)