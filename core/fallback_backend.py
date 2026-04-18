from core.claude_code_backend import BackendLimitError


class FallbackBackend:
    """
    Tenta cada backend em ordem. Avança para o próximo apenas em BackendLimitError.
    Qualquer outro erro propaga imediatamente — não mascara falhas reais.
    """

    def __init__(self, backends: list):
        if not backends:
            raise ValueError("FallbackBackend requer ao menos um backend")
        self._backends = backends

    def complete(self, prompt: str, system: str = "",
                 model: str = "sonnet", max_tokens: int = 4096) -> dict:
        last_limit_error = None
        for backend in self._backends:
            try:
                return backend.complete(
                    prompt=prompt,
                    system=system,
                    model=model,
                    max_tokens=max_tokens,
                )
            except BackendLimitError as e:
                last_limit_error = e
                continue
        raise last_limit_error

    def is_available(self) -> bool:
        return any(
            getattr(b, "is_available", lambda: True)()
            for b in self._backends
        )
