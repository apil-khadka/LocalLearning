# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Students and teachers at schools in Nepal are equally primary users.
Students use the school-local portal to read books and, when enabled, ask questions about learning material.
Teachers and school staff curate, review, and import content for those learners.

## Product Purpose

Digital Himalaya makes learning materials available on a school's local network when internet access is unreliable.
It combines a local book library with an optional tutor grounded in reviewed textbooks.
Success means students can reach useful school-approved resources locally and teachers can manage those resources without depending on a continuous internet connection.

## Positioning

The school runs the portal on a local server and serves learning resources over its own network.
The optional tutor uses imported textbook passages as evidence and identifies when it cannot find a matching passage.

## Operating Context

Schools provision content and models while online, then evaluate the portal with student devices while disconnected from the WAN.
Teachers or staff import PDF and text resources with grade, subject, chapter, source, and license information.
Students browse the local catalog and use the tutor when the school has enabled its required services.
Kolibri is a separate classroom service for its own courses, accounts, activities, and progress.

## Capabilities and Constraints

The portal provides a local book catalog, student book access, an optional textbook-grounded tutor, and a protected staff workspace.
The interface supports English and Nepali, and the project packages the app and optional Kolibri service in containers.
The tutor is disabled by default and depends on separately configured chat, embedding, and vector services.
Digital Himalaya does not create student accounts, retain tutor chat history, or synchronize Kolibri accounts or progress.
Deployment must suit modest school hardware and unreliable WAN access.
Imported material needs rights review, source attribution, and teacher review before classroom use.
Current prototype content is not approved as a Nepal curriculum set.

## Brand Commitments

The product name is Digital Himalaya.
The repository includes the project mark at `frontend/public/brand/digital-himalaya-mark.png`.
The student interface includes English and Nepali text.

## Evidence on Hand

The repository contains a working web portal, API, local content workflow, optional Kolibri link, and automated software checks.
`content/sample/force-and-motion.txt` is an original demonstration note for import and retrieval testing.
Private text-only Wikibooks test content and revision manifests are stored under ignored `content/private/` and are not included in the public repository.
The walkthrough at `site/assets/videos/prototype-walkthrough.mp4` shows a local portal, a tutor answer, and Kolibri's first-run screen.
There is no documented school pilot, curriculum approval, or field-validated learning outcome.

## Product Principles

Keep core reading available on the school network after online provisioning.
Require teacher review and traceable source information for learning content.
Keep AI optional, disclose when an answer is not grounded in a textbook passage, and avoid implying curriculum approval.
Keep Kolibri's classroom records and content separate from Digital Himalaya's tutor and catalog.
Fit the project to modest hardware and make external services configurable.

## Accessibility & Inclusion

Keep student workflows usable on phones and small screens on school Wi-Fi.
Support English and Nepali interface text and keyboard-accessible controls.
The language coverage and curricular suitability of imported learning material remain unverified and need local teacher review.
