#!/usr/bin/env python3
"""Check Stoa's OpenAI and Verda credentials without displaying secret values.

Default: OpenAI GET /models and Verda OAuth authentication only.
--balance adds Verda GET /balance. --inference explicitly opts into one small,
potentially billable OpenAI Responses request. Nothing provisions resources.

Uses only Python's standard library. The env file accepts simple KEY=VALUE
lines, optional `export`, and optional matching outer quotes. It performs no
shell expansion, interpolation, multiline parsing, or inline-comment parsing.
Values in the selected file override matching process environment variables.

Endpoint sources, verified 2026-11-13:
https://developers.openai.com/api/reference/resources/models/methods/list
https://developers.openai.com/api/reference/resources/responses/methods/create
https://api.verda.com/v1/docs (OAuth quick start and GET /v1/balance)
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import socket
import ssl
import sys
import time
from urllib import error, request


DEFAULT_ENV = Path.home() / ".config/stoa-junction-2026/secrets.env"
GEMINI_ENV = DEFAULT_ENV.with_name('gemini.env')
DEFAULT_MODEL = "gpt-6-astra"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
RETRYABLE_HTTP = {429, 500, 502, 503, 504}
ENV_KEYS = {
    "OPENAI_API_KEY", "OPENAI_PROJECT_ID", "VERDA_CLIENT_ID",
    "VERDA_CLIENT_SECRET", "VERDA_PROJECT_ID",
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "STOA_PROVIDER", "STOA_MODEL",
    "STOA_MAX_MODEL_CALLS", "STOA_INPUT_USD_PER_MILLION",
    "STOA_CACHED_INPUT_USD_PER_MILLION", "STOA_OUTPUT_USD_PER_MILLION",
    "STOA_SMALL_IMAGE_CROPS",
}


class HealthError(Exception):
    """Carries only a fixed error code and optional numeric HTTP status."""

    def __init__(self, code: str, http_status: int | None = None):
        super().__init__(code)
        self.code = code
        self.http_status = http_status


class NoRedirect(request.HTTPRedirectHandler):
    """Do not forward authorization headers or credential bodies elsewhere."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_config(path: Path, *, include_environment=True) -> dict[str, str]:
    config = {key: os.environ[key] for key in ENV_KEYS if key in os.environ} if include_environment else {}
    try:
        if not path.exists():
            return config
        if path.stat().st_size > 128 * 1024:
            raise HealthError("env_file_too_large")
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        raise HealthError("env_file_unreadable") from None
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise HealthError("unsupported_env_file_syntax")
        value = value.strip()
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise HealthError("unsupported_env_file_syntax")
            value = value[1:-1]
        if key in ENV_KEYS:
            config[key] = value
    return config


def load_runtime_config(path: Path = DEFAULT_ENV, gemini_path: Path | None = GEMINI_ENV):
    """Use the private Gemini sidecar only once it contains a key."""
    config = load_config(path)
    selected = os.environ.get('STOA_PROVIDER')
    if gemini_path is not None and (selected is None or selected.strip().lower() == 'gemini'):
        values = load_config(gemini_path, include_environment=False)
        if ((values.get('GEMINI_API_KEY') or values.get('GOOGLE_API_KEY'))
                and values.get('STOA_PROVIDER', 'gemini').strip().lower() == 'gemini'):
            values['STOA_PROVIDER'] = 'gemini'
            values.setdefault('STOA_MODEL', 'gemini-4-carbon')
            for key, value in values.items():
                if key.startswith('STOA_') or key in {'GEMINI_API_KEY', 'GOOGLE_API_KEY'}:
                    config[key] = value
    for key in ENV_KEYS:
        if key in os.environ:
            config[key] = os.environ[key]
    return config


def create_ssl_context(ca_file: Path | None = None) -> ssl.SSLContext:
    """Verify TLS using an explicit CA file or a trusted macOS bundle fallback."""
    if ca_file is not None:
        try:
            return ssl.create_default_context(cafile=str(ca_file.expanduser()))
        except (OSError, ssl.SSLError):
            raise HealthError("ca_file_unusable") from None
    paths = ssl.get_default_verify_paths()
    system_bundle = Path("/etc/ssl/cert.pem")
    if (sys.platform == "darwin" and paths.cafile is None
            and paths.capath is None and system_bundle.is_file()):
        try:
            return ssl.create_default_context(cafile=str(system_bundle))
        except (OSError, ssl.SSLError):
            raise HealthError("system_ca_bundle_unusable") from None
    try:
        return ssl.create_default_context()
    except (OSError, ssl.SSLError):
        raise HealthError("default_ca_store_unusable") from None


def request_json(url: str, *, method: str = "GET", headers=None, payload=None,
                 timeout: float = 15.0, retries: int = 1,
                 ssl_context: ssl.SSLContext | None = None):
    """Return JSON; discard HTTP error bodies and never echo request values."""
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Accept": "application/json", "User-Agent": "stoa-healthcheck/1"}
    request_headers.update(headers or {})
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    opener = request.build_opener(
        NoRedirect(), request.HTTPSHandler(context=ssl_context or create_ssl_context())
    )
    for attempt in range(retries + 1):
        try:
            req = request.Request(url, data=data, headers=request_headers, method=method)
            with opener.open(req, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise HealthError("response_too_large")
            try:
                return json.loads(raw)
            except (ValueError, UnicodeError):
                raise HealthError("invalid_json_response") from None
        except error.HTTPError as exc:
            status = exc.code
            exc.close()  # Do not read or log server error bodies.
            if status in RETRYABLE_HTTP and attempt < retries:
                time.sleep(min(2 ** attempt, 4))
                continue
            code = {
                400: "request_rejected", 401: "authentication_failed",
                402: "payment_required", 403: "permission_denied",
                404: "endpoint_or_model_unavailable", 429: "rate_or_quota_limited",
            }.get(status, "http_error")
            raise HealthError(code, status) from None
        except (error.URLError, TimeoutError, socket.timeout, OSError):
            if attempt < retries:
                time.sleep(min(2 ** attempt, 4))
                continue
            raise HealthError("network_or_tls_error") from None
    raise HealthError("request_failed")


def error_result(exc: HealthError) -> dict:
    result = {"status": "error", "error": exc.code}
    if exc.http_status is not None:
        result["http_status"] = exc.http_status
    return result


def check_openai(config: dict, args) -> dict:
    key = config.get("OPENAI_API_KEY", "")
    if not key:
        return {"status": "missing_credentials", "missing": ["OPENAI_API_KEY"]}
    headers = {"Authorization": "Bearer " + key}
    project = config.get("OPENAI_PROJECT_ID")
    if project:
        headers["OpenAI-Project"] = project
    try:
        body = request_json("https://api.openai.com/v1/models", headers=headers,
                            timeout=args.timeout, retries=args.retries,
                            ssl_context=args.ssl_context)
        if not isinstance(body, dict) or not isinstance(body.get("data"), list):
            raise HealthError("unexpected_models_response")
        model_ids = {item.get("id") for item in body["data"] if isinstance(item, dict)
                     and isinstance(item.get("id"), str)}
        result = {"status": "ok", "models_count": len(model_ids),
                  "selected_model_listed": args.model in model_ids,
                  "inference": {"status": "not_requested"}}
    except HealthError as exc:
        result = error_result(exc)
        if not args.inference:
            return result
    if args.inference:
        try:
            # No automatic retries: an uncertain POST may already have incurred cost.
            body = request_json(
                "https://api.openai.com/v1/responses", method="POST", headers=headers,
                payload={"model": args.model, "input": "Reply with exactly OK.",
                         "max_output_tokens": 64, "store": False,
                         "reasoning": {"effort": "low"}},
                timeout=args.timeout, retries=0, ssl_context=args.ssl_context,
            )
            if not isinstance(body, dict):
                raise HealthError("unexpected_inference_response")
            output = body.get("output", [])
            texts = [part.get("text", "") for item in output if isinstance(item, dict)
                     for part in item.get("content", []) if isinstance(part, dict)
                     and part.get("type") == "output_text"] if isinstance(output, list) else []
            completed = body.get("status") == "completed"
            result["inference"] = {
                "status": "ok" if completed and texts else "incomplete",
                "completed": completed,
                "expected_output": "".join(texts).strip() == "OK",
            }
            usage = body.get("usage")
            if isinstance(usage, dict):
                result["inference"]["usage"] = {
                    name: usage[name] for name in ("input_tokens", "output_tokens", "total_tokens")
                    if type(usage.get(name)) is int and usage[name] >= 0
                }
        except HealthError as exc:
            result["inference"] = error_result(exc)
    return result


def check_verda(config: dict, args) -> dict:
    missing = [name for name in ("VERDA_CLIENT_ID", "VERDA_CLIENT_SECRET") if not config.get(name)]
    if missing:
        return {"status": "missing_credentials", "missing": missing}
    try:
        body = request_json(
            "https://api.verda.com/v1/oauth2/token", method="POST",
            payload={"grant_type": "client_credentials", "client_id": config["VERDA_CLIENT_ID"],
                     "client_secret": config["VERDA_CLIENT_SECRET"]},
            timeout=args.timeout, retries=args.retries, ssl_context=args.ssl_context,
        )
        if not isinstance(body, dict) or not isinstance(body.get("access_token"), str) or not body["access_token"]:
            raise HealthError("unexpected_oauth_response")
        token = body["access_token"]  # Memory only; neither token is persisted or displayed.
        result = {"status": "ok", "balance": {"status": "not_requested"}}
        expiry = body.get("expires_in")
        if type(expiry) is int and expiry >= 0:
            result["access_token_expires_in_seconds"] = expiry
        # This is configured context, not an assertion about the token's project.
        project = config.get("VERDA_PROJECT_ID", "")
        if re.fullmatch(r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}", project):
            result["configured_project_id"] = project
    except HealthError as exc:
        return error_result(exc)
    if args.balance:
        try:
            body = request_json("https://api.verda.com/v1/balance",
                                headers={"Authorization": "Bearer " + token},
                                timeout=args.timeout, retries=args.retries,
                                ssl_context=args.ssl_context)
            amount = body.get("amount") if isinstance(body, dict) else None
            currency = body.get("currency") if isinstance(body, dict) else None
            if type(amount) not in (int, float) or not math.isfinite(amount) or currency not in ("usd", "eur"):
                raise HealthError("unexpected_balance_response")
            result["balance"] = {"status": "ok", "amount": amount,
                                 "currency": currency, "funded": amount > 0}
        except HealthError as exc:
            result["balance"] = error_result(exc)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--ca-file", type=Path, help="Trusted PEM CA bundle; TLS verification remains enabled")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Responses model (default: %(default)s)")
    parser.add_argument("--inference", action="store_true", help="Opt into one small, potentially billable OpenAI request")
    parser.add_argument("--balance", action="store_true", help="Read Verda balance after authenticating")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-request timeout, 1–60 seconds")
    parser.add_argument("--retries", type=int, choices=range(3), default=1, help="Retries for read/auth requests, 0–2; inference is never retried")
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or not 1 <= args.timeout <= 60:
        print(json.dumps({"status": "error", "error": "timeout_must_be_1_to_60_seconds"}))
        return 2
    try:
        args.ssl_context = create_ssl_context(args.ca_file)
        config = load_config(args.env_file.expanduser())
    except HealthError as exc:
        print(json.dumps(error_result(exc), sort_keys=True))
        return 2
    results = {}
    for name, check in (("openai", check_openai), ("verda", check_verda)):
        try:
            results[name] = check(config, args)
        except Exception:
            # Third-party response surprises must not expose request data in a traceback.
            results[name] = {"status": "error", "error": "unexpected_check_failure"}
    passed = all(result.get("status") == "ok" for result in results.values())
    if args.inference:
        passed = passed and results["openai"].get("inference", {}).get("status") == "ok"
    if args.balance:
        passed = passed and results["verda"].get("balance", {}).get("status") == "ok"
    print(json.dumps({"status": "ok" if passed else "needs_attention", "checks": results}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
