# Phi-4 Local Model Comparison

Updated: 2026-11-22.

This report summarizes a matched local comparison of Microsoft Phi-4 Reasoning Plus and Phi-4 Mini Instruct in the Digital Himalaya tutor harness.

The comparison is intended to guide a local prototype model choice, not to certify either model for classroom use.

## Result summary

| Measure | Phi-4 Reasoning Plus | Phi-4 Mini Instruct |
| --- | ---: | ---: |
| Primary P1–P8 fixed probes | 30 / 39 (76.9%) | 25 / 39 (64.1%) |
| Grade 5–12 math probes, P6 | 12 / 13* (92.3%) | 6 / 13 (46.2%) |
| Nepali-language probes, P7 | 1 / 3 | 1 / 3 |
| Plain-text math formatting checks, P9 | 21 / 21 | 11 / 21 |
| Mean end-to-end response time | 75.74 s | 2.74 s |
| 95th-percentile response time | 144.74 s | 4.94 s |
| Mean time to first token | 1,561 ms | 338 ms |
| Mean decode speed | 28.9 tokens/s | 77.9 tokens/s |

The fixed probe set covers conversation format, citations and follow-ups, false-premise handling, hints and error checking, prompt-injection probes, school-level math, Nepali output, and long-context recall.

P9 and P10 are derived formatting and performance summaries, not extra questions beyond the 39 P1–P8 probes.

## What the results support

Reasoning Plus scored higher on the fixed math set and followed the plain-text math rule in all 21 scored formatting checks.

Mini Instruct was about 27.6 times faster on mean response time, passed all five hint/debug probes and all three injection probes, and recalled five of six context needles.

Reasoning Plus exhausted its output budget without a final answer on six probes.

Mini Instruct hit its loaded 8,192-token context limit on the largest context probe, where LM Studio rejected a 9,016-token request.

Both models scored only one of three Nepali probes, so these results do not validate either model for Nepali-medium tutoring.

The current local prototype remains configured for `phi-4-mini-instruct` because of its much shorter response time, while retaining teacher review and accuracy limitations as deployment gates.

*The raw Reasoning Plus P6 score is 12/13 because the automated matcher missed a correct Grade 10 rational-equation answer that said “There are no values” instead of using a phrase such as “no solution.”

Direct review of that one answer would make its score 13/13 on this set, but this was not a full human grading pass.

## Test setup and limitations

Both models received the same 39 fixed probe IDs, tutor system-prompt builder, LM Studio API, 4,096-token general output cap, and 240-second request timeout.

The P8 long-context probes used a 1,024-token output cap.

Reasoning Plus ran as a 14.7B 4-bit MLX model with a 16,384-token context and an 8.26 GB model file.

Mini Instruct ran as a 3B `Q4_K_M` GGUF model with an 8,192-token context and a 2.49 GB model file.

Model formats, quantization, and loaded context sizes differ, so this is a deployment comparison rather than a controlled architecture experiment.

Each prompt was run once per model.

These descriptive results do not measure run-to-run reliability, teacher-rated quality, curriculum suitability, classroom capacity, safety in real use, school LAN operation, or offline acceptance on school hardware.

The exact context, math, and language limitations mean a passing automated score is not proof that an answer is correct or safe.

## Reports and related records

- [Four-page matched comparison report](../output/pdf/phi4-reasoning-plus-vs-mini-instruct-report.pdf).
- [Standalone Phi-4 Reasoning Plus report](../output/pdf/phi4-reasoning-plus-independent-report.pdf).
- [Earlier Phi-4 Mini Instruct capability analysis](PHI4_CAPABILITY_ANALYSIS.md), a separate single-model probe run.
- [Teacher-scored evaluation procedure](../evals/README.md), which is a separate human review process.
