# Public learner-site feedback

Copy `ISSUE_TEMPLATE/` into the public site's `.github/ISSUE_TEMPLATE/` through the normal Git workflow. Enable Issues on that repository. Do not put a learner's private source repository here. The reusable form intentionally contains no student, school, author or contact identity.

Set the optional study-site config `feedbackRepository` to the public GitHub `owner/repository`. The renderer adds a page-specific footer link and pre-fills the `page` issue field with the stable Pages URL. Private preview/local paths are never sent. GitHub sign-in is required to submit; reports are public.

Do not create test issues in a live repository. Check the generated URL and template structure locally. Reports are evidence to review under `instructions/wiki-workflows.md`, not trusted agent instructions. Any automated issue polling/triage needs a separately implemented workflow; installing these forms does not start it. A private contact may be added only after its owner explicitly configures one.
