#!/bin/bash
# Harness-home clean-up before every start (review finding: a role's home is writable by the
# LLM running in it, so anything that changes a harness's behaviour is removed and only the
# login is kept). Runs as container root, before the preflight.
#   kept:    ~/.claude/.credentials.json, ~/.claude.json (without MCP servers and hooks),
#            ~/.codex/auth.json, session history
#   removed: settings, instructions, hooks, agents, commands, skills, plugins, output
#            styles, MCP configuration, shell and tool start-up files
set -u
home=/home/agent
[ -d "$home" ] || exit 0

# A symlinked config directory is removed as a link; rm never follows links.
for dir in .claude .codex .config .local .npm; do
    [ -L "$home/$dir" ] && rm -f "$home/$dir"
done
rm -rf -- \
    "$home/.claude/settings.json" "$home/.claude/settings.local.json" \
    "$home/.claude/CLAUDE.md" "$home/.claude/hooks" "$home/.claude/agents" \
    "$home/.claude/commands" "$home/.claude/skills" "$home/.claude/plugins" \
    "$home/.claude/output-styles" "$home/.claude/mcp.json" "$home/.claude/statusline.sh" \
    "$home/.codex/AGENTS.md" "$home/.codex/AGENTS.override.md" "$home/.codex/config.toml" \
    "$home/.codex/prompts" "$home/.codex/skills" "$home/.codex/rules" \
    "$home/.codex/hooks.json" "$home/.config" "$home/.mcp.json" "$home/CLAUDE.md" \
    "$home/AGENTS.md" "$home/.bashrc" "$home/.profile" "$home/.bash_profile" \
    "$home/.bash_login" "$home/.npmrc" "$home/.gitconfig" "$home/.curlrc" "$home/.wgetrc"

# ~/.claude.json holds the login state plus per-user/per-project MCP servers and hooks.
state="$home/.claude.json"
if [ -L "$state" ]; then
    rm -f "$state"
elif [ -f "$state" ]; then
    node -e '
        const fs = require("fs"); const f = process.argv[1];
        let d; try { d = JSON.parse(fs.readFileSync(f, "utf8")); } catch { process.exit(0); }
        const drop = ["mcpServers", "hooks", "enabledMcpjsonServers", "disabledMcpjsonServers"];
        for (const k of drop) delete d[k];
        for (const p of Object.values(d.projects || {})) for (const k of drop) delete p[k];
        fs.writeFileSync(f, JSON.stringify(d, null, 2));
    ' "$state" || exit 1
fi
exit 0
