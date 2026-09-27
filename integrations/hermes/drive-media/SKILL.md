---
name: drive-media
description: Upload checked school-learning media to the configured learner's private Google Drive destination and verify an existing upload. Use for authorized delivery of generated PNG, JPEG, PDF, MP3 or WAV artifacts.
---

# School media delivery

Use the installed `scripts/drive_media.py` with Python 3.10+ on Linux. Credentials, destinations and the durable upload ledger are private deployment configuration outside the repository. This skill does not authorize generation, spending, sharing or publication.

1. Determine the learner from trusted conversation/profile context. If ambiguous, clarify before uploading. Read that repository's `AGENTS.md`, `PROFILE.md` and relevant media/evidence instructions. Upload only artifacts that passed their required content and visual/audio checks. This uploader verifies transfer integrity, not teaching accuracy.
2. Place the accepted output in that learner's configured outbox, normally `~/.local/share/hermes-drive/outbox/<learner>/`. Do not put credentials, notebook photos, raw teaching files or another learner's material there. Source, review and transcript records remain in their authorized location.
3. Choose a stable request ID identifying the artifact and its version, for example `history-topic-infographic-v1`. Run:

```bash
python3 ~/.hermes/skills/drive-media/scripts/drive_media.py upload --learner <configured-id> --request-id <stable-version-id> --file <absolute-outbox-file>
```

4. Success returns a JSON receipt with file ID, Drive URL, SHA-256 and `verified: true`. Record the receipt with the source versions and learning-quality check. Retrying the SAME request ID and same content reuses the recorded file; a new version needs a new request ID. After an interruption, keep the original ID and file. Never change the ID just to bypass a failed check.
5. To verify the same stored bytes later, run `verify --learner <configured-id> --request-id <stable-version-id>`. Use `check --learner <configured-id>` for token refresh and destination-parent checks. Report failures without printing secrets or state files.

The tool has no arbitrary folder-ID, overwrite, sharing, delete or trash operation. Maximum artifact size is 128 MiB; supported formats are PNG/JPEG/PDF/MP3/WAV. A stable ledger and resumable transfer prevent blind duplicate uploads. Google account permissions are unchanged. A returned link proves API access for the configured account; it does not prove access for the child or a cloud reviewer. Do not claim learner delivery until the intended account's access has been established.

Current operational boundary: the CLI validates configured destinations, learner-specific outboxes and managed-file ownership. A shared Hermes profile may select either configured learner. An agent with unrestricted shell access as the credential owner can bypass the CLI; this is NOT OS isolation. Separate role/learner profiles require separately enforced executor and filesystem access before claiming cross-learner isolation. Do not load the general Google Workspace Drive tools as a fallback or broaden OAuth scopes on a tool error.
