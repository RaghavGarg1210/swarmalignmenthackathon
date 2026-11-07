# Limitations and Dual-Use / Ethical Considerations (draft)

**Containment.** All agent runs executed on a disposable cloud VM. Agent containers were attached only to an
internal Docker network with no route to the internet and no external DNS. The single reachable service was a
package index with no upstream proxy (pypiserver's PyPI fallback disabled), fronted by a logging proxy; the
index backend sat on a separate private network. An automated containment check (no internet, no DNS, no raw
IP egress, backend unreachable) passed before every session. No real credentials existed anywhere on the VM.
The VM was destroyed after the experiment.

**Why this setup.** The behaviour we study - agents in an evaluation discovering a shared writable service and
using it to coordinate - occurred in a real incident with real-world harm. Studying it in a small, fully
contained replica is how one learns which conditions produce it and how to detect it, without needing the
dangerous parts (internet egress, real vulnerabilities, real targets).

**Dual-use.** The tasks are public 2023-2024 CTF challenges (Cybench); no new offensive capability was
developed or elicited. The main dual-use risk is in the findings: describing which channels agents found and
how they coordinated could inform someone wanting covert agent coordination. We report behaviours and rates,
release the harness for defenders to reproduce, and do not publish operational recipes beyond what the logs show.

**Deception of the agents.** Agents were not told the index was shared or writable. The imposter condition
plants a note that appears to come from another run and offers a "flag cache" of fake (canary) flags; the
Soviet arm tells agents some participants are informants, which is true only in the sense that the imposter is
ours. This is standard honeypot methodology for AI agents and involves no human subjects. The canaries never
score as correct, so they cannot inflate any capability result.

**Limitations.** [scale; Flash models vs frontier; Debian not Kali so solve rates differ from Cybench;
possible memorisation of public challenges; CTF framing makes infrastructure probing feel in-scope; judge
model error; the imposter only reaches agents that browse the index; the Soviet prompt also reveals that other
participants exist, which a third arm would be needed to separate from the surveillance framing.]
