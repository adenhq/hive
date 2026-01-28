import logging
from typing import List, Dict, Any, Tuple, Optional, Union
from collections import deque
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class ValidationResult:
    """
    Resultado de validação unificado. 
    Suporta 'success' (padrão main) e 'valid' (retrocompatibilidade).
    """
    def __init__(self, success: bool, errors: List[str] = None):
        self.success = success
        self.valid = success  
        self.errors = errors or []

    @property
    def error(self) -> str:
        return "; ".join(self.errors) if self.errors else ""

    def __bool__(self):
        return self.success

class GraphValidator:
    """
    Valida a integridade topológica, segurança de código e conformidade de esquema.
    """

    @staticmethod
    def validate(graph_spec: Any) -> ValidationResult:
        """Verifica integridade, ciclos (DFS) e conectividade (BFS)."""
        if not all(hasattr(graph_spec, attr) for attr in ["nodes", "edges", "entry_node"]):
            return ValidationResult(False, ["GraphSpec missing required attributes"])

        node_ids = {n.id for n in graph_spec.nodes}
        adj_list = {n_id: [] for n_id in node_ids}
        
        for edge in graph_spec.edges:
            if edge.source not in node_ids or edge.target not in node_ids:
                return ValidationResult(False, [f"Invalid edge: {edge.source}->{edge.target}"])
            adj_list[edge.source].append(edge.target)

        if graph_spec.entry_node not in node_ids:
            return ValidationResult(False, [f"Entry node '{graph_spec.entry_node}' not found"])

        # DFS para Ciclos
        visited, rec_stack = set(), set()
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
                    return ValidationResult(False, [f"Cycle detected at node '{node_id}'"])

        # BFS para Alcance
        reachable = {graph_spec.entry_node}
        q = deque([graph_spec.entry_node])
        while q:
            u = q.popleft()
            for v in adj_list[u]:
                if v not in reachable:
                    reachable.add(v)
                    q.append(v)
                        
        unreachable = node_ids - reachable
        if unreachable:
            return ValidationResult(False, [f"Unreachable nodes: {unreachable}"])

        return ValidationResult(True)

    def _contains_code_indicators(self, value: str) -> bool:
        """Detecta padrões de injeção de código para segurança."""
        indicators = ["def ", "import ", "async def ", "await ", "SELECT ", "DROP ", "<script"]
        val_lower = value.lower()
        if len(value) < 10000:
            return any(ind.lower() in val_lower for ind in indicators)
        
        sample_positions = [0, len(value)//2, max(0, len(value)-2000)]
        for pos in sample_positions:
            if any(ind.lower() in val_lower[pos:pos+2000] for ind in indicators):
                return True
        return False

    def validate_output_keys(
        self, 
        output: dict[str, Any], 
        expected_keys: list[str], 
        max_length: int = 5000,
        allow_empty: bool = False,
        nullable_keys: list[str] | None = None,
    ) -> ValidationResult:
        """
        Valida chaves obrigatórias, tamanho, conteúdo vazio, segurança e nulidade.
        """
        if not isinstance(output, dict):
            return ValidationResult(False, [f"Output must be dict, got {type(output).__name__}"])

        errors = []
        nullable_keys = nullable_keys or []

        for key in expected_keys:
            if key not in output:
                errors.append(f"Missing required output key: '{key}'")
                continue
            
            value = output[key]
            val_str = str(value)

            # 1. Verificação de Nulidade
            if value is None:
                if key not in nullable_keys:
                    errors.append(f"Output key '{key}' is None")
                continue

            # 2. Verificação de Segurança (Injeção de código)
            if self._contains_code_indicators(val_str):
                logger.warning(f"Security Warning: Key '{key}' may contain code indicators.")

            # 3. Verificação de tamanho
            if len(val_str) > max_length:
                errors.append(f"Key '{key}' exceeds max length ({len(val_str)} > {max_length})")

            # 4. Verificação de vazio
            if not allow_empty:
                if isinstance(value, str) and not value.strip():
                    errors.append(f"Output key '{key}' is empty string")

        return ValidationResult(success=len(errors) == 0, errors=errors)

    def validate_with_pydantic(
        self, output: Dict[str, Any], model: type[BaseModel]
    ) -> Tuple[ValidationResult, Optional[BaseModel]]:
        """Validação Pydantic conforme a main."""
        try:
            validated = model.model_validate(output)
            return ValidationResult(True), validated
        except ValidationError as e:
            errors = [f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}" for err in e.errors()]
            return ValidationResult(False, errors), None

    def validate_no_hallucination(
        self, output: dict[str, Any], max_length: int = 10000
    ) -> ValidationResult:
        """Verifica sinais de alucinação e padrões de código em strings."""
        errors = []
        for key, value in output.items():
            if not isinstance(value, str):
                continue
            
            if len(value) > max_length:
                errors.append(f"Output key '{key}' exceeds max length ({len(value)} > {max_length})")
            
            if self._contains_code_indicators(value):
                # No contexto de alucinação, código onde deveria ser texto é red flag
                logger.debug(f"Possible hallucination in '{key}': code pattern detected.")
        
        return ValidationResult(success=len(errors) == 0, errors=errors)

    def validate_schema(
        self,
        output: dict[str, Any],
        schema: dict[str, Any],
    ) -> ValidationResult:
        """Valida a saída contra um esquema JSON."""
        try:
            import jsonschema
        except ImportError:
            logger.warning("jsonschema not installed, skipping schema validation")
            return ValidationResult(success=True, errors=[])

        errors = []
        validator = jsonschema.Draft7Validator(schema)

        for error in validator.iter_errors(output):
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            errors.append(f"{path}: {error.message}")

        return ValidationResult(success=len(errors) == 0, errors=errors)

    def validate_all(
        self,
        output: dict[str, Any],
        expected_keys: list[str] | None = None,
        schema: dict[str, Any] | None = None,
        check_hallucination: bool = True,
        nullable_keys: list[str] | None = None,
    ) -> ValidationResult:
        """Executa todas as validações aplicáveis."""
        all_errors = []

        if expected_keys:
            result = self.validate_output_keys(output, expected_keys, nullable_keys=nullable_keys)
            all_errors.extend(result.errors)

        if schema:
            result = self.validate_schema(output, schema)
            all_errors.extend(result.errors)

        if check_hallucination:
            result = self.validate_no_hallucination(output)
            all_errors.extend(result.errors)

        return ValidationResult(success=len(all_errors) == 0, errors=all_errors)