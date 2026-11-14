# Kolibri integration research

Date: 2026-11-04. Local Kolibri: 0.19.5 (container `ghcr.io/learningequality/kolibri:0.19.5`).

## Question

How should Digital Himalaya integrate with Kolibri beyond a managed link plus
HTTP reachability probe, while keeping the product's offline-first and
account-separation guarantees?

## Sourced facts

- Kolibri exposes its Django models as JSON through Django REST Framework
  viewsets. The content app registers `channel`, `contentnode`,
  `contentnode_tree`, `contentnode_search`, `contentnodeprogress`,
  `contentnode_granular`, and `remotechannel` routes.
  Source: [Server/client communication](https://kolibri-dev.readthedocs.io/en/develop/dataflow/index.html).
- Local observation (unauthenticated, no session): `GET /api/public/info/`
  returns the server version; `GET /api/content/channel/` returns locally
  imported channel metadata; `GET /api/content/contentnode_search/` answers
  searches over imported content; `GET /api/auth/facility/` returns facility
  metadata. `GET /api/device/deviceinfo/` and `GET /api/content/remotechannel/`
  require authentication.
- Local observation: the dev instance held two channel metadata records
  (Touchable Earth, PhET) with `available: false` and zero resources until
  `kolibri manage importcontent network <channel-id>` was run. After the
  import, PhET reports `available: true` with 1,175 resources.
- Channel Learn pages deep-link as `/en/learn/#/topics/c/<contentnode-id>`,
  where the channel root node id equals the channel id. This format is used
  consistently across community examples, e.g. a channel link posted by
  Learning Equality staff.
  Source: [community thread with `/en/learn/#/topics/c/2a4def...` links](https://community.learningequality.org/t/khan-academy-human-biology-exercises-missing-images/1549).
- `importcontent` supports partial imports via `--node_ids`,
  `--exclude_node_ids`, and `--manifest`, so a school can import a reviewed
  subset instead of a whole channel.
  Source: [Kolibri command-line guide](https://kolibri.readthedocs.io/en/latest/manage/command_line.html)
  and `kolibri manage help importcontent` on the pinned 0.19.5 image.
- Upstream channel sizes (2026-11-04, English catalog): PhET 565 resources /
  ~239 MB; Touchable Earth 366 resources / ~3.8 GB. Local PhET v18 reports
  1,175 resources after import.
  Source: `https://kolibri-catalog-en.learningequality.org/api/public/v1/channels/`.

## Options compared

1. Managed link only (previous state). Cheapest and safest, but learners
   cannot see which courses exist without leaving the portal, and staff get
   no signal about imported content.
2. Read-only catalog surfacing (chosen). The API reads the unauthenticated
   channel/version endpoints through the configured probe URL and serves a
   sanitized catalog with Learn-page deep links. No credentials, no account
   or progress access, works offline on the school LAN, and fails back to
   the plain reachability status when the catalog calls fail.
3. Authenticated staff view (device info, tasks, remote channels). More
   operational detail, but requires storing a Kolibri session or service
   credential server-side and widens the trust boundary. Rejected for now;
   staff already manage Kolibri in its own interface.
4. Account or progress synchronization. Rejected: PRODUCT.md commits to
   keeping Kolibri classroom records separate from the portal, and Kolibri
   offers no supported learner-provisioning API for this use.
5. Tutor ingestion of Kolibri content. Rejected for now: channel licenses
   need per-resource rights review, and Kolibri resources (video, HTML5,
   exercises) do not fit the PDF/text chunk pipeline.

## Decision

Implement option 2: `GET /api/kolibri/channels` plus version/channel counts
on the existing `/api/services` Kolibri entry, a student Courses page with
per-channel deep links, and staff visibility of version and ready-channel
counts. Import one curriculum-relevant channel (PhET) into the dev instance
so the integration is verifiable end to end. Keep sign-in, accounts,
classes, and progress entirely inside Kolibri.
