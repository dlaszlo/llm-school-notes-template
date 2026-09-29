#!/usr/bin/env node
// No installation side effects: see instructions/page-check.md for the one-time setup.
try {
  const {run}=await import('./page-check/runner.mjs');
  await run(process.argv.slice(2));
} catch(error) {
  console.error('Page check failed:', error.message);
  console.error('Use the pinned setup in instructions/page-check.md. No dependency or browser is installed by this command.');
  process.exitCode=2;
}
