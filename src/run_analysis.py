from __future__ import annotations

import json
from datetime import datetime

from update_dashboard import BEIJING, DEFAULT_PUBLIC_ROOT, build_analysis_payload, load_previous, write_outputs


def main() -> int:
    payload = load_previous()
    if not payload:
        raise SystemExit("尚无标准化数据，请先运行 python src/update_dashboard.py")
    analysis, judgement = build_analysis_payload(payload.get("indicators", []), payload.get("pending", []), datetime.now(BEIJING))
    payload["analysis"] = analysis
    payload["macro_judgement"] = judgement
    write_outputs(payload, DEFAULT_PUBLIC_ROOT)
    print(json.dumps({"generated_at": analysis["generated_at"], "gpt_status": judgement.get("gpt_status")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
