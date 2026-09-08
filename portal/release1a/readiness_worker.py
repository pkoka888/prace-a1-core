"""Internal disposable probe. Never processes documents or runs migrations."""
import json


def main():
    try:
        import django
        django.setup()
        from .readiness_runner import collect_checks
        result = collect_checks()
    except Exception:
        result = {'status':'not_ready','reason':'probe_initialization_failed'}
    print(json.dumps(result, separators=(',', ':')))


if __name__ == '__main__':
    main()
