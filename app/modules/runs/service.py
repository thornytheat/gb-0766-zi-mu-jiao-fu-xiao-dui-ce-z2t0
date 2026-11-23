from datetime import datetime, timezone
from time import perf_counter_ns
from app.digests import digest, encode, fingerprints
from app.pipeline import inspect
from app.problems import Rejection
from app.settings import VERSION


def record(store, material):
    start = perf_counter_ns()
    hashes = fingerprints(material)
    key = digest(encode([VERSION, hashes]))
    stages = inspect(material)
    result_hash = digest(encode(stages))
    manifest = dict(id=key, version=VERSION, input_sha256=hashes, result_sha256=result_hash,
                    created_at=datetime.now(timezone.utc).isoformat(), elapsed_us=(perf_counter_ns() - start) // 1000)
    actual, reused = store.publish(key, dict(manifest=manifest, original=material, stages=stages))
    if actual['manifest']['result_sha256'] != result_hash or digest(encode(actual['stages'])) != result_hash:
        raise Rejection('DRIFT', '复算与已归档结果不一致', 409)
    return dict(summary(actual), reused=reused)


def summary(record):
    return dict(id=record['manifest']['id'], manifest=record['manifest'], counts=record['stages']['balance']['counts'])
