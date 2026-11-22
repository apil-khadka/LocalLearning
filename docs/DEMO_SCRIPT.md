# Offline acceptance and evidence

Do this on the actual Ubuntu server, router/AP, power system and client devices before claiming a working school demonstration.
Automated tests and a GitHub Pages website do not replace these checks.
Record date, software/image/model versions, embedding model digest, hardware, client count and measurement method privately.
Publish only approved non-identifying evidence.

## Required checks

| Check | Passing evidence |
| --- | --- |
| Provisioned resources | Chosen local chat model present; approved searchable book; imported Kiwix article and Kolibri resource available if those services are part of the deployment |
| No internet | WAN physically disconnected; phone cellular off; assets, API, local Phi-4 chat, and imported books work on school Wi-Fi; no request leaves for hosted chat |
| Real inference | A new question returns output from the configured local LM Studio model through the portal; no test fixture server is running |
| Grounding | Answer source chip opens the correct document/PDF page and the passage is relevant |
| No-match handling | Wrong grade/chapter and unrelated questions show no false retrieved citations |
| Teaching notes | A teacher drafts a note from reviewed book pages and a second teacher approves it; students see it on the Study page only after approval, and its page link opens the right page |
| Tutor modes | Hint mode withholds the answer and debug mode names the error across the teacher-authored task set, scored with the [evaluation tool](TEACHING_NOTES.md#teacher-scored-evaluation) |
| Kolibri classroom roles | A learner opens an assigned course; a coach can assign reviewed material; role boundaries and progress behave as configured |
| Language | Teacher/fluent reviewer checks English and Nepali answers, mathematical meaning and readability |
| Staff boundary | Student cannot access staff API/port, NOMAD, router administration, SSH, Ollama or Qdrant |
| Staff operation | Authorized staff tunnel, token sign-in and permitted import work; wrong token fails |
| Library capacity | 12 simultaneous browser clients load approved content; record actual latency/errors |
| AI admission | Three concurrent questions complete or receive an honest busy response; measure accepted-request latency and recovery |
| Content quality | Image-only PDF reports OCR required; missing pages are flagged; no false success |
| Recovery | Restart server/router without WAN; catalog, vector index, models, article and video survive |
| Backup | Restore the coordinated catalog/files/vector backup in a disposable environment and repeat a cited query |

The local Phi-4 matched comparison is summarized in [PHI4_MODEL_COMPARISON.md](PHI4_MODEL_COMPARISON.md).
It found a strong response-time advantage for Mini Instruct and material math, language, and context limits; it does not meet the teacher-review gate below.

Prepare a teacher-reviewed task set including in-scope questions, no-match questions, Nepali, misleading premises and document-injection attempts.
Use the project's proposed quality gate of at least 80% teacher-rated acceptable replies with zero severe unsafe outputs, and agree on acceptable measured latency before enabling student use.
This is a pilot gate, not a measured claim about the current model.
Disable AI if the review fails; retained approved library content must remain accessible.

Run an extended content session, document power/temperature behavior, and rehearse UPS shutdown and restart with the actual hardware.
An untested CPU/RAM specification does not establish classroom concurrency or operating time.

## Evidence record

Keep a checklist with pass/fail, observed values, issue reference and next owner for every check.
Do not log student prompts, names or identifiable photos by default.
Record service request IDs for failures without copying private questions into bug reports.
Separate automated software verification, target-hardware measurements and educational review in any public progress update.
