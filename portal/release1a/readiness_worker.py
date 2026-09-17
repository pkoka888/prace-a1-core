"""Internal disposable probe. Never processes documents or runs migrations."""
import json
import time


def main():
    started = time.monotonic()

    def progress(phase):
        print(json.dumps({'event': 'progress', 'phase': phase,
                          'elapsed_ms': round((time.monotonic() - started) * 1000)}),
              flush=True)

    progress('initialization')
    try:
        import django
        django.setup()
        from .readiness_runner import collect_checks
        startup_ms = round((time.monotonic() - started) * 1000)
        result = collect_checks(progress=progress)
        result['startup_ms'] = startup_ms
    except Exception:
        result = {'status':'not_ready','reason':'probe_initialization_failed'}
    print(json.dumps(result, separators=(',', ':')))


if __name__ == '__main__':
    main()
