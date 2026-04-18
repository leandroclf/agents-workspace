import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource


_tracer: trace.Tracer = None
_meter: metrics.Meter = None
_request_counter = None
_token_counter = None
_cost_counter = None


def setup_telemetry(service_name: str = "claude-workspace"):
    global _tracer, _meter, _request_counter, _token_counter, _cost_counter

    resource = Resource.create({"service.name": service_name})
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    _tracer = trace.get_tracer(__name__)

    meter_provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter(__name__)

    _request_counter = _meter.create_counter(
        "claude_requests_total",
        description="Total requests to Claude API"
    )
    _token_counter = _meter.create_counter(
        "claude_tokens_total",
        description="Total tokens consumed"
    )
    _cost_counter = _meter.create_counter(
        "claude_cost_usd_total",
        description="Total cost in USD"
    )


def record_api_call(model: str, task_type: str,
                    input_tokens: int, output_tokens: int, cost_usd: float):
    if _request_counter:
        _request_counter.add(1, {"model": model, "task_type": task_type})
    if _token_counter:
        _token_counter.add(input_tokens + output_tokens,
                           {"model": model, "token_type": "total"})
    if _cost_counter:
        _cost_counter.add(cost_usd, {"model": model})


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        setup_telemetry()
    return _tracer
