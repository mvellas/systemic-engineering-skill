#!/usr/bin/env python3
"""Optional browser E2E via Chromium DevTools; no web server or remote asset required."""

from __future__ import annotations
import argparse, asyncio, base64, json, subprocess, sys
from pathlib import Path
import websockets

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".agents/skills/systemic-engineering"
sys.path.insert(0, str(SKILL / "scripts"))
from sef_runtime import reports


async def verify(chromium, suffix):
    evidence = ROOT / ".evidence/browser"
    evidence.mkdir(parents=True, exist_ok=True)
    files = []
    for kind in ("business", "software", "critical"):
        p = ROOT / "examples/output" / (kind + suffix)
        if not p.exists():
            raise RuntimeError("Generate examples first: " + kind)
        rendered = reports.render(p)
        files.extend(
            [
                (kind, "report", Path(rendered["report"])),
                (kind, "dashboard", Path(rendered["dashboard"])),
            ]
        )
        receipt = ROOT / ".evidence" / (kind + suffix + ".json")
        record = json.loads(receipt.read_text())
        record["outputs"] = rendered
        receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    proc = subprocess.Popen(
        [
            str(chromium),
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            "--remote-debugging-port=0",
            "about:blank",
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        text=True,
    )
    results = []
    try:
        while True:
            line = proc.stderr.readline()
            if "DevTools listening on " in line:
                url = line.strip().split("DevTools listening on ")[1]
                break
            if not line and proc.poll() is not None:
                raise RuntimeError("Chromium failed to start")
        async with websockets.connect(url, max_size=50000000) as ws:
            counter = 0
            events = []

            async def command(method, params=None, session=None):
                nonlocal counter
                counter += 1
                mid = counter
                msg = {"id": mid, "method": method, "params": params or {}}
                if session:
                    msg["sessionId"] = session
                await ws.send(json.dumps(msg))
                while True:
                    r = json.loads(await ws.recv())
                    if r.get("id") == mid:
                        if "error" in r:
                            raise RuntimeError(r["error"])
                        return r.get("result", {})
                    events.append(r)

            target = await command("Target.createTarget", {"url": "about:blank"})
            session = (
                await command(
                    "Target.attachToTarget",
                    {"targetId": target["targetId"], "flatten": True},
                )
            )["sessionId"]

            async def evaluate(expression):
                value = await command(
                    "Runtime.evaluate",
                    {"expression": expression, "returnByValue": True},
                    session,
                )
                if value.get("exceptionDetails"):
                    raise RuntimeError(value["exceptionDetails"])
                return value["result"].get("value")

            await command("Page.enable", session=session)
            await command("Runtime.enable", session=session)
            await command("Network.enable", session=session)
            for width, height in [(1440, 1000), (390, 844)]:
                await command(
                    "Emulation.setDeviceMetricsOverride",
                    {
                        "width": width,
                        "height": height,
                        "deviceScaleFactor": 1,
                        "mobile": False,
                    },
                    session,
                )
                for kind, doc, path in files:
                    events.clear()
                    await command("Page.navigate", {"url": path.as_uri()}, session)
                    for attempt in range(150):
                        ready = await evaluate(
                            'document.readyState==="complete"&&location.href==='
                            + json.dumps(path.as_uri())
                        )
                        if ready:
                            break
                        await asyncio.sleep(0.05)
                    await asyncio.sleep(0.1)
                    result = json.loads(
                        await evaluate(
                            'JSON.stringify({title:document.title,overflow:document.documentElement.scrollWidth>innerWidth+1,images:[...document.images].every(x=>x.complete&&x.naturalWidth>0),badAnchors:[...document.querySelectorAll("a[href^=\\"#\\"]")].filter(a=>!document.getElementById(a.getAttribute("href").slice(1))).map(a=>a.getAttribute("href")),chart:document.querySelectorAll("#chart-main svg").length,sourceLinks:document.querySelectorAll(".sources a[href^=\\"https://\\"]").length})'
                        )
                    )
                    result.update(
                        kind=kind,
                        document=doc,
                        viewport=[width, height],
                        ready=ready,
                        path=str(path.relative_to(ROOT)),
                    )
                    if kind != "critical":
                        # Actual selector, slider, metric and replay controls must change rendered readings.
                        await evaluate(
                            'document.getElementById("metric-select").value="customers";document.getElementById("metric-select").dispatchEvent(new Event("change"))'
                        )
                        await evaluate(
                            'document.getElementById("period-slider").value="2";document.getElementById("period-slider").dispatchEvent(new Event("input"))'
                        )
                        result["sliderChanged"] = await evaluate(
                            'document.getElementById("period-label").textContent==="Período 2"'
                        )
                        await evaluate(
                            'document.querySelector("[data-panel=agents-panel]").click()'
                        )
                        result["tabChanged"] = await evaluate(
                            '!document.getElementById("agents-panel").hidden&&document.getElementById("time-panel").hidden'
                        )
                        await evaluate(
                            'const sel=document.getElementById("run-select");const index=[...sel.options].findIndex(o=>o.dataset.engine==="agents");if(index>=0){sel.selectedIndex=index;sel.dispatchEvent(new Event("change"))}'
                        )
                        result["agentNodes"] = await evaluate(
                            'document.querySelectorAll("#chart-agents circle").length'
                        )
                        await evaluate(
                            'document.querySelector("[data-panel=time-panel]").click()'
                        )
                        await command(
                            "Emulation.setEmulatedMedia",
                            {
                                "features": [
                                    {
                                        "name": "prefers-reduced-motion",
                                        "value": "reduce",
                                    }
                                ]
                            },
                            session,
                        )
                        await evaluate('document.getElementById("play").click()')
                        result["reducedMotionRespected"] = await evaluate(
                            'document.getElementById("play").textContent==="Reproduzir"'
                        )
                        await command(
                            "Emulation.setEmulatedMedia", {"features": []}, session
                        )
                    result["financialControls"] = await evaluate(
                        '(()=>{const d=JSON.parse(document.getElementById("study-data").textContent);const i=d.runs.findIndex(r=>(r.result.summary||[]).some?.(s=>s.financial));if(i<0)return true;const sel=document.getElementById("run-select");sel.selectedIndex=i;sel.dispatchEvent(new Event("change"));const m=document.getElementById("metric-select");m.value="accounts_receivable";m.dispatchEvent(new Event("change"));return !m.selectedOptions[0].disabled&&document.querySelectorAll("#chart-main svg").length===1;})()'
                    )
                    result["campaignCharts"] = await evaluate(
                        '(()=>{const d=JSON.parse(document.getElementById("study-data").textContent);return (d.campaigns||[]).filter(c=>c.analysis?.ranking?.length).every(c=>document.getElementById("chart-campaign-"+c.id)?.querySelector("svg"));})()'
                    )
                    if doc == "report":
                        result["artifactCount"] = await evaluate(
                            'document.querySelectorAll(".artifact").length'
                        )
                        await evaluate(
                            'const f=document.getElementById("search");f.value="persona";f.dispatchEvent(new Event("input"))'
                        )
                        result["searchWorks"] = await evaluate(
                            'document.querySelectorAll(".artifact:not([hidden])").length<22'
                        )
                        await evaluate(
                            'const field=document.getElementById("search");field.value="";field.dispatchEvent(new Event("input"))'
                        )
                    result["exceptions"] = [
                        x["params"]
                        for x in events
                        if x.get("method") == "Runtime.exceptionThrown"
                    ]
                    result["remoteRequests"] = [
                        x["params"]["request"]["url"]
                        for x in events
                        if x.get("method") == "Network.requestWillBeSent"
                        and x["params"]["request"]["url"].startswith(
                            ("http:", "https:")
                        )
                    ]
                    if kind == "business":
                        screenshot = await command(
                            "Page.captureScreenshot", {"format": "png"}, session
                        )
                        (evidence / f"{kind}-{doc}-{width}.png").write_bytes(
                            base64.b64decode(screenshot["data"])
                        )
                    results.append(result)
            status = (
                "pass"
                if all(
                    r["ready"]
                    and not r["overflow"]
                    and r["images"]
                    and not r["badAnchors"]
                    and not r["exceptions"]
                    and not r["remoteRequests"]
                    and r.get("financialControls", True)
                    and r.get("campaignCharts", True)
                    and r.get("sliderChanged", True)
                    and r.get("tabChanged", True)
                    and r.get("reducedMotionRespected", True)
                    and r.get("searchWorks", True)
                    and r.get("artifactCount", 22) == 22
                    and r.get("agentNodes", 1) > 0
                    for r in results
                )
                else "fail"
            )
            output = {"status": status, "total": len(results), "checks": results}
            (evidence / "results.json").write_text(
                json.dumps(output, ensure_ascii=False, indent=2)
            )
            print(
                json.dumps(
                    {
                        "status": status,
                        "checks": len(results),
                        "failed": [
                            r
                            for r in results
                            if r["overflow"] or r["exceptions"] or r["badAnchors"]
                        ],
                    }
                )
            )
            return status == "pass"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--chromium", type=Path, required=True)
    p.add_argument("--suffix", default="-final")
    args = p.parse_args()
    sys.exit(0 if asyncio.run(verify(args.chromium, args.suffix)) else 1)
