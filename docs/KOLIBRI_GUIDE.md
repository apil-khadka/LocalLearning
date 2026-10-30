# Kolibri content operations

This guide describes how school staff can select, import, update, and verify learning content in Kolibri alongside the Digital Himalaya portal.

Digital Himalaya links to Kolibri and checks whether it is reachable.
Kolibri remains responsible for its facility, user accounts, classes, lessons, quizzes, content, and progress.
The two systems do not share sign-in, user records, or course progress.

## Before using Kolibri

1. Start the embedded service with `make education-up`, or confirm the existing Kolibri service is running.
2. Set `KOLIBRI_PUBLIC_URL` to the URL a staff browser and student browser can reach.
3. Set `KOLIBRI_PROBE_URL` to the address the API container can reach.
4. Recreate the API after changing either value with `docker compose up -d --force-recreate api`.
5. Open the protected staff workspace and use the Kolibri status and **Open Kolibri** link.
6. Complete Kolibri's own first-run device and facility setup before assigning content.

The default embedded service uses port 8092 for Kolibri's web interface and port 8093 for its content transfer interface.
Both ports bind to loopback by default.
For a school LAN installation, use a reserved server address and the network policy in [NETWORK.md](NETWORK.md) before changing the bind address.
The configured public URL must work from the browser that opens the staff workspace.

## Set up accounts and responsibilities

Kolibri uses its own accounts and roles.
Create named accounts for the staff who will manage the device, coach classes, and support learners.
Keep the initial super-admin credentials in the school's private credential store.
Give device content-management permission only to staff who are responsible for selecting and updating channels.
Use coach accounts to manage classes, lessons, quizzes, and learner progress.
Create learner accounts or groups using the school's normal student privacy process.
Never place Kolibri credentials in `.env`, this repository, or the Digital Himalaya staff token field.

## Review content rights before import

Kolibri software and Kolibri learning channels are separately licensed.
Before importing a channel, record its title, source, license or permission, attribution requirements, and the reviewer/date.
Check whether the channel and its media may be stored on this school server and shared with the intended learners.
Keep the required attribution with the school's content inventory.
If rights or redistribution terms are unclear, do not import the material until they are confirmed.

Digital Himalaya's textbook importer accepts approved PDF and text documents for its own library and tutor workflow.
It does not convert those files into Kolibri learning resources.
To publish custom Kolibri materials, prepare a channel through Kolibri Studio, or use an existing channel whose terms and content have been reviewed.

## Import a channel

1. Sign in to Kolibri with an account permitted to manage device resources.
2. Open **Device > Channels > Import**.
3. Choose a source: Kolibri Studio, a connected Kolibri device on the local network, or a prepared Kolibri storage drive.
4. Select the reviewed channel and the resources needed by the school's learners.
5. Review the selection, start the import, and follow its progress in Kolibri's task manager.
6. Open several imported resources from a learner account and confirm that required audio, video, and interactive media work while disconnected from the WAN.
7. Assign appropriate lessons or resources to a test class before using them with a full cohort.

For a fully offline site, prepare or export the channel to storage while a source device is connected, then import that channel from the prepared drive at the school.
Keep a record of which channel version was transferred.
An HTTP reachability check from Digital Himalaya does not prove that a course or its media has been imported.

## Update a channel safely

1. Schedule the update for a quiet period when learners are not using the affected channel.
2. Sign in with device content-management permission and open **Device > Channels > Manage**.
3. Select **View changes** for the channel.
4. Review the summary of added, updated, moved, and deleted resources.
5. Confirm the channel update only after the changes and rights have been reviewed.
6. Select the resources to update and monitor the task manager until it reports completion.
7. Open changed resources from a learner account.
8. Recheck lessons and quizzes that use resources which were changed, moved, or removed.
9. Record the channel version/date and the staff member who reviewed the update.

Do not update channels during high learner activity.
An update can make a lesson or quiz that references a changed or moved resource stop working, so verify these activities after every channel update.
For a site without internet, use an approved channel export or storage-drive update workflow and apply the same review and verification steps.

## Verify the integration

- The staff workspace reports Kolibri as reachable and its **Open Kolibri** link opens from the staff browser.
- A learner can open an assigned channel resource through Kolibri from a student device.
- A coach can see the intended class and assign a reviewed lesson or quiz.
- A learner can complete the test activity and the coach can see its progress in Kolibri.
- The same learning activity works with the WAN disconnected when the site expects offline operation.
- No learner account or progress is expected to appear in Digital Himalaya's document catalog or AI tutor.

The integration is a managed link and service check, not automatic channel import, account provisioning, grade synchronization, or tutor ingestion.

## Back up and upgrade

Back up Kolibri's data separately from Digital Himalaya's content volume and Qdrant index.
Use Kolibri's supported channel export for portable content copies and a stopped-volume backup for the complete installation, including facility configuration and learner records.
Store backups privately and test restoration on a disposable deployment before relying on them.

Channel updates and Kolibri application upgrades are different operations.
Keep the Compose image pinned to a reviewed Kolibri version, back up the data volume, read the release notes, and test an image upgrade with a copy of the deployment before changing a school installation.
Do not use `docker compose down -v` as a stop or update command because it deletes named volumes.

## Official references

- [Kolibri initial setup](https://kolibri.readthedocs.io/en/latest/install/initial_setup.html)
- [Kolibri user roles](https://kolibri.readthedocs.io/en/latest/manage/user_roles.html)
- [Kolibri permissions](https://kolibri.readthedocs.io/en/latest/manage/permissions.html)
- [Importing and updating channels and resources](https://kolibri.readthedocs.io/en/latest/manage/resources.html)
- [Kolibri command-line management](https://kolibri.readthedocs.io/en/latest/manage/command_line.html)
- [Digital Himalaya installation and backup guide](INSTALL.md)
