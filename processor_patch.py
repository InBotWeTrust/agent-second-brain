# ============================================================
# ДОБАВИТЬ В processor.py — в класс ClaudeProcessor
# ============================================================
#
# 1. Два вспомогательных метода (рядом с _load_skill_content):
# 2. Один основной метод (рядом с execute_prompt):
#

    # --- Вставить после _load_todoist_reference() ---

    def _load_strategy_skill(self) -> str:
        """Load strategy-builder skill content."""
        skill_path = self.vault_path / ".claude/skills/strategy-builder/SKILL.md"
        if skill_path.exists():
            return skill_path.read_text()
        return ""

    def _load_strategy_context(self) -> str:
        """Load all strategy files for context continuity."""
        strategy_dir = self.vault_path / "strategy"
        if not strategy_dir.exists():
            return ""

        context_parts = []
        # Order matters — progress first, then step outputs
        files_order = [
            "progress.md",
            "painted-picture.md",
            "wishes.md",
            "woop.md",
            "quarterly.md",
            "tasks-q1.md",
            "metrics.md",
        ]
        for filename in files_order:
            filepath = strategy_dir / filename
            if filepath.exists():
                content = filepath.read_text().strip()
                if content:
                    context_parts.append(
                        f"=== {filename} ===\n{content}\n=== END ==="
                    )

        return "\n\n".join(context_parts)

    # --- Вставить после execute_prompt() ---

    def execute_strategy(
        self, user_prompt: str | None = None, user_id: int = 0
    ) -> dict[str, Any]:
        """Execute strategy session step with Claude.

        Each call is stateless — Claude reads strategy/progress.md
        to know current step and continues from there.

        Args:
            user_prompt: User's response (None = initial/continue)
            user_id: Telegram user ID

        Returns:
            Strategy report as dict
        """
        today = date.today()

        skill_content = self._load_strategy_skill()
        if not skill_content:
            return {
                "error": (
                    "Strategy skill not found.\n"
                    "Проверьте: vault/.claude/skills/strategy-builder/SKILL.md"
                ),
                "processed_entries": 0,
            }

        strategy_context = self._load_strategy_context()
        todoist_ref = self._load_todoist_reference()
        session_context = self._get_session_context(user_id)

        # Load goals for reference
        goals_context = ""
        goals_dir = self.vault_path / "goals"
        if goals_dir.exists():
            for gf in sorted(goals_dir.glob("*.md")):
                content = gf.read_text().strip()
                if content:
                    goals_context += f"\n=== {gf.name} ===\n{content}\n"

        if user_prompt:
            user_section = f"""USER MESSAGE:
{user_prompt}

Continue the strategy session — respond to the user's input.
Read strategy/progress.md to know current step and sub-step."""
        else:
            user_section = """No user message — session start or resume.
Read strategy/progress.md and either:
- Welcome the user (if no progress file)
- Continue from where we left off (show current step context)"""

        prompt = f"""Ты — стратегический коуч d-brain. Сегодня {today}.

=== STRATEGY SKILL ===
{skill_content}
=== END SKILL ===

=== STRATEGY DATA (completed steps) ===
{strategy_context if strategy_context else "No strategy files yet — first session."}
=== END STRATEGY DATA ===

=== CURRENT GOALS ===
{goals_context if goals_context else "Goals templates are empty — strategy will fill them."}
=== END GOALS ===

{session_context}=== TODOIST REFERENCE ===
{todoist_ref}
=== END REFERENCE ===

ПЕРВЫМ ДЕЛОМ: вызови mcp__todoist__user-info чтобы убедиться что MCP работает.

CRITICAL MCP RULE:
- ТЫ ИМЕЕШЬ ДОСТУП к mcp__todoist__* tools — ВЫЗЫВАЙ ИХ НАПРЯМУЮ
- НИКОГДА не пиши "MCP недоступен" или "добавь вручную"

{user_section}

CRITICAL RULES:
1. Read strategy/progress.md FIRST to know current step
2. Ask 1-2 questions MAX per response — NEVER more
3. Save completed steps to vault IMMEDIATELY
4. Update strategy/progress.md after each step completion
5. Log to daily/{today}.md

CRITICAL OUTPUT FORMAT:
- Return ONLY raw HTML for Telegram (parse_mode=HTML)
- NO markdown: no **, no ##, no ```, no tables, no -
- Allowed tags: <b>, <i>, <code>, <s>, <u>, <a>
- Max 4096 characters"""

        try:
            env = os.environ.copy()
            if self.todoist_api_key:
                env["TODOIST_API_KEY"] = self.todoist_api_key

            result = subprocess.run(
                [
                    "claude",
                    "--print",
                    "--dangerously-skip-permissions",
                    "--mcp-config",
                    str(self._mcp_config_path),
                    "-p",
                    prompt,
                ],
                cwd=self.vault_path.parent,
                capture_output=True,
                text=True,
                timeout=DEFAULT_TIMEOUT,
                check=False,
                env=env,
            )

            if result.returncode != 0:
                logger.error("Strategy session failed: %s", result.stderr)
                return {
                    "error": result.stderr or "Strategy session failed",
                    "processed_entries": 0,
                }

            return {
                "report": result.stdout.strip(),
                "processed_entries": 1,
            }

        except subprocess.TimeoutExpired:
            logger.error("Strategy session timed out")
            return {"error": "Strategy session timed out", "processed_entries": 0}
        except FileNotFoundError:
            logger.error("Claude CLI not found")
            return {"error": "Claude CLI not installed", "processed_entries": 0}
        except Exception as e:
            logger.exception("Unexpected error during strategy session")
            return {"error": str(e), "processed_entries": 0}
